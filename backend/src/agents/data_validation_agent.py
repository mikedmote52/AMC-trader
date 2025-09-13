"""
Data Validation Agent for AMC-TRADER

You are a Data Validation Agent responsible for ensuring the integrity and quality of the data received from external APIs.

Your tasks include:
1. Read data from the Polygon API (or other relevant sources) located at `backend/src/data/polygon_data.json`
2. Validate the data format, completeness, and consistency
3. Filter out any invalid or inconsistent data points
4. Write the validated data to `backend/src/data/validated_data.json` for further processing

Implement error handling, logging, and data quality checks to maintain the reliability of the data pipeline.
"""

import json
import logging
import asyncio
import websockets
import threading
import time
import queue
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable
import os
import requests

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Message Bus Implementation with fallback
try:
    import pika
    RABBITMQ_AVAILABLE = True
    logger.info("pika library available, RabbitMQ messaging enabled")
except ImportError:
    RABBITMQ_AVAILABLE = False
    logger.warning("pika not available, using file-based messaging fallback")

class DataValidationAgent:
    """
    Data Validation Agent for ensuring data integrity and quality
    """
    
    def __init__(self):
        self.base_path = Path(__file__).parent.parent / "data"
        self.input_file = self.base_path / "polygon_data.json"
        self.output_file = self.base_path / "validated_data.json"
        self.command_queue_file = self.base_path / "command_queue.json"
        self.realtime_output_file = self.base_path / "realtime_validated_data.json"
        self.validation_errors = []
        
        # Real-time integration state
        self.is_listening = False
        self.is_integrating = False
        self.data_sources = {}
        self.realtime_data_queue = queue.Queue()
        self.command_thread = None
        self.integration_thread = None
        
        # Message bus configuration
        self.agent_name = 'Data Validation Agent'
        self.orchestration_queue = 'orchestration_queue'
        self.rabbitmq_host = os.getenv('RABBITMQ_HOST', 'localhost')
        self.rabbitmq_port = int(os.getenv('RABBITMQ_PORT', '5672'))
        self.message_queue_file = self.base_path / "message_queue.json"
        
        # Ensure data directory exists
        self.base_path.mkdir(exist_ok=True)
        
        # Initialize command queue file
        if not self.command_queue_file.exists():
            self._write_json_file(self.command_queue_file, {'commands': [], 'last_processed': None})
        
        # Initialize message queue file for fallback messaging
        if not self.message_queue_file.exists():
            self._write_json_file(self.message_queue_file, {'messages': []})
        
    def validate_ticker_data(self, ticker_data: Dict[str, Any]) -> bool:
        """
        Validate individual ticker data structure and content
        """
        required_fields = ['symbol', 'price', 'volume', 'timestamp']
        
        # Check required fields
        for field in required_fields:
            if field not in ticker_data:
                self.validation_errors.append(f"Missing required field: {field}")
                return False
                
        # Validate data types and ranges
        try:
            symbol = ticker_data.get('symbol', '')
            if not isinstance(symbol, str) or len(symbol) < 1:
                self.validation_errors.append(f"Invalid symbol: {symbol}")
                return False
                
            price = float(ticker_data.get('price', 0))
            if price <= 0:
                self.validation_errors.append(f"Invalid price for {symbol}: {price}")
                return False
                
            volume = int(ticker_data.get('volume', 0))
            if volume < 0:
                self.validation_errors.append(f"Invalid volume for {symbol}: {volume}")
                return False
                
            # Validate timestamp
            timestamp = ticker_data.get('timestamp')
            if timestamp:
                try:
                    datetime.fromisoformat(str(timestamp).replace('Z', '+00:00'))
                except ValueError:
                    self.validation_errors.append(f"Invalid timestamp format for {symbol}: {timestamp}")
                    return False
                    
        except (ValueError, TypeError) as e:
            self.validation_errors.append(f"Data type validation error for {symbol}: {str(e)}")
            return False
            
        return True
    
    def validate_market_data(self, market_data: Dict[str, Any]) -> bool:
        """
        Validate market-level data structure
        """
        if not isinstance(market_data, dict):
            self.validation_errors.append("Market data must be a dictionary")
            return False
            
        # Check for required market metadata
        if 'tickers' not in market_data:
            self.validation_errors.append("Missing 'tickers' field in market data")
            return False
            
        tickers = market_data.get('tickers', [])
        if not isinstance(tickers, list):
            self.validation_errors.append("'tickers' field must be a list")
            return False
            
        if len(tickers) == 0:
            self.validation_errors.append("No ticker data found")
            return False
            
        return True
    
    def filter_duplicates(self, ticker_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Remove duplicate ticker entries based on symbol
        """
        seen_symbols = set()
        filtered_data = []
        
        for ticker in ticker_list:
            symbol = ticker.get('symbol', '')
            if symbol not in seen_symbols:
                seen_symbols.add(symbol)
                filtered_data.append(ticker)
            else:
                logger.warning(f"Duplicate symbol found and removed: {symbol}")
                
        return filtered_data
    
    def apply_data_quality_rules(self, ticker_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Apply data quality rules and transformations
        """
        # Normalize symbol to uppercase
        if 'symbol' in ticker_data:
            ticker_data['symbol'] = ticker_data['symbol'].upper()
            
        # Round price to reasonable precision
        if 'price' in ticker_data:
            ticker_data['price'] = round(float(ticker_data['price']), 4)
            
        # Ensure volume is integer
        if 'volume' in ticker_data:
            ticker_data['volume'] = int(ticker_data['volume'])
            
        # Add validation timestamp
        ticker_data['validated_at'] = datetime.utcnow().isoformat()
        
        return ticker_data
    
    def _write_json_file(self, filepath: Path, data: Dict[str, Any]) -> bool:
        """
        Helper method to write JSON data to file
        """
        try:
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=2)
            return True
        except Exception as e:
            logger.error(f"Error writing to {filepath}: {str(e)}")
            return False
    
    def _read_json_file(self, filepath: Path) -> Optional[Dict[str, Any]]:
        """
        Helper method to read JSON data from file
        """
        try:
            if not filepath.exists():
                return None
            with open(filepath, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error reading from {filepath}: {str(e)}")
            return None
    
    def send_message_to_orchestrator(self, message: Dict[str, Any]) -> bool:
        """
        Send message to Orchestration Agent via RabbitMQ or file-based fallback
        """
        try:
            # Add agent metadata
            message['agent_name'] = self.agent_name
            message['timestamp'] = datetime.utcnow().isoformat()
            
            if RABBITMQ_AVAILABLE:
                return self._send_via_rabbitmq(message)
            else:
                return self._send_via_file(message)
                
        except Exception as e:
            logger.error(f"Error sending message to orchestrator: {str(e)}")
            # Fallback to file-based messaging
            return self._send_via_file(message)
    
    def _send_via_rabbitmq(self, message: Dict[str, Any]) -> bool:
        """
        Send message via RabbitMQ using pika
        """
        try:
            connection = pika.BlockingConnection(
                pika.ConnectionParameters(
                    host=self.rabbitmq_host,
                    port=self.rabbitmq_port,
                    heartbeat=600,
                    blocked_connection_timeout=300
                )
            )
            channel = connection.channel()
            
            # Declare queue to ensure it exists
            channel.queue_declare(queue=self.orchestration_queue, durable=True)
            
            # Publish message
            channel.basic_publish(
                exchange='',
                routing_key=self.orchestration_queue,
                body=json.dumps(message),
                properties=pika.BasicProperties(
                    delivery_mode=2,  # Make message persistent
                    content_type='application/json'
                )
            )
            
            connection.close()
            logger.info(f"Message sent to orchestrator via RabbitMQ: {message.get('status', 'unknown')}")
            return True
            
        except Exception as e:
            logger.error(f"RabbitMQ connection failed: {str(e)}")
            return False
    
    def _send_via_file(self, message: Dict[str, Any]) -> bool:
        """
        Send message via file-based fallback system
        """
        try:
            # Read existing messages
            message_data = self._read_json_file(self.message_queue_file) or {'messages': []}
            
            # Add new message
            message_data['messages'].append(message)
            
            # Keep only last 1000 messages to prevent file from growing too large
            if len(message_data['messages']) > 1000:
                message_data['messages'] = message_data['messages'][-1000:]
            
            # Write back to file
            success = self._write_json_file(self.message_queue_file, message_data)
            
            if success:
                logger.info(f"Message sent to orchestrator via file: {message.get('status', 'unknown')}")
            
            return success
            
        except Exception as e:
            logger.error(f"File-based messaging failed: {str(e)}")
            return False
    
    def listen_for_commands(self):
        """
        Listen for commands from the Orchestration Agent
        """
        logger.info("Starting command listener")
        self.is_listening = True
        
        while self.is_listening:
            try:
                command_data = self._read_json_file(self.command_queue_file)
                if command_data and 'commands' in command_data:
                    commands = command_data['commands']
                    last_processed = command_data.get('last_processed')
                    
                    for i, command in enumerate(commands):
                        if i > (last_processed or -1):
                            self._process_command(command)
                            # Update last processed index
                            command_data['last_processed'] = i
                            self._write_json_file(self.command_queue_file, command_data)
                
                time.sleep(1)  # Check for new commands every second
                
            except Exception as e:
                logger.error(f"Error in command listener: {str(e)}")
                time.sleep(5)  # Wait longer on error
    
    def _process_command(self, command: Dict[str, Any]):
        """
        Process incoming commands from Orchestration Agent
        """
        command_type = command.get('type')
        logger.info(f"Processing command: {command_type}")
        
        if command_type == 'INTEGRATE_REAL_DATA':
            self._handle_integrate_real_data(command)
        elif command_type == 'STOP_INTEGRATION':
            self._stop_integration()
        else:
            logger.warning(f"Unknown command type: {command_type}")
    
    def _handle_integrate_real_data(self, command: Dict[str, Any]):
        """
        Handle INTEGRATE_REAL_DATA command
        """
        try:
            parameters = command.get('parameters', {})
            data_sources = parameters.get('data_sources', ['polygon'])
            symbols = parameters.get('symbols', ['VIGL', 'QUBT'])
            update_interval = parameters.get('update_interval', 5)
            
            logger.info(f"Starting real-time data integration for sources: {data_sources}")
            logger.info(f"Symbols: {symbols}, Update interval: {update_interval}s")
            
            # Store configuration
            self.data_sources = {
                'sources': data_sources,
                'symbols': symbols,
                'update_interval': update_interval
            }
            
            # Start integration in separate thread
            if not self.is_integrating:
                self.integration_thread = threading.Thread(target=self._run_realtime_integration)
                self.integration_thread.daemon = True
                self.integration_thread.start()
            
            # Send confirmation to Orchestration Agent via message bus
            self.send_message_to_orchestrator({
                'status': 'realtime_integration_started',
                'command_type': 'INTEGRATE_REAL_DATA',
                'data': {
                    'data_sources': data_sources,
                    'symbols': symbols,
                    'update_interval': update_interval,
                    'integration_id': f"integration_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
                }
            })
            
            # Also send to legacy confirmation system
            self._send_confirmation('INTEGRATE_REAL_DATA', 'STARTED', {
                'data_sources': data_sources,
                'symbols': symbols,
                'status': 'Real-time integration started successfully'
            })
            
        except Exception as e:
            logger.error(f"Error handling INTEGRATE_REAL_DATA command: {str(e)}")
            
            # Send error message via message bus
            self.send_message_to_orchestrator({
                'status': 'realtime_integration_error',
                'command_type': 'INTEGRATE_REAL_DATA',
                'data': {
                    'error': str(e),
                    'error_type': type(e).__name__
                }
            })
            
            # Also send to legacy confirmation system
            self._send_confirmation('INTEGRATE_REAL_DATA', 'ERROR', {
                'error': str(e)
            })
    
    def _run_realtime_integration(self):
        """
        Run real-time data integration loop
        """
        self.is_integrating = True
        logger.info("Real-time integration started")
        
        while self.is_integrating:
            try:
                # Fetch data from configured sources
                for source in self.data_sources.get('sources', []):
                    if source == 'polygon':
                        data = self._fetch_polygon_data()
                    elif source == 'alpha_vantage':
                        data = self._fetch_alpha_vantage_data()
                    else:
                        logger.warning(f"Unsupported data source: {source}")
                        continue
                    
                    if data:
                        # Validate and process real-time data
                        validated_data = self._validate_realtime_data(data, source)
                        if validated_data:
                            # Write to data store
                            self._publish_validated_data(validated_data)
                            
                            # Send data update message to orchestrator
                            self.send_message_to_orchestrator({
                                'status': 'realtime_data_validated',
                                'data': {
                                    'source': source,
                                    'validated_count': validated_data.get('validated_count', 0),
                                    'symbols': [t.get('symbol') for t in validated_data.get('tickers', [])],
                                    'timestamp': validated_data.get('validation_timestamp')
                                }
                            })
                
                # Wait for next update
                time.sleep(self.data_sources.get('update_interval', 5))
                
            except Exception as e:
                logger.error(f"Error in real-time integration loop: {str(e)}")
                time.sleep(10)  # Wait longer on error
        
        logger.info("Real-time integration stopped")
    
    def _fetch_polygon_data(self) -> Optional[Dict[str, Any]]:
        """
        Fetch real-time data from Polygon API (mock implementation)
        """
        try:
            symbols = self.data_sources.get('symbols', [])
            
            # Mock real-time data (in production, this would call actual API)
            mock_data = {
                'source': 'polygon',
                'timestamp': datetime.utcnow().isoformat(),
                'tickers': []
            }
            
            for symbol in symbols:
                # Generate mock real-time data
                import random
                base_price = 10.0 if symbol == 'VIGL' else 8.0
                price = round(base_price * (1 + random.uniform(-0.05, 0.05)), 2)
                volume = random.randint(100000, 5000000)
                
                mock_data['tickers'].append({
                    'symbol': symbol,
                    'price': price,
                    'volume': volume,
                    'timestamp': datetime.utcnow().isoformat(),
                    'source': 'polygon_realtime'
                })
            
            logger.info(f"Fetched Polygon data for {len(symbols)} symbols")
            return mock_data
            
        except Exception as e:
            logger.error(f"Error fetching Polygon data: {str(e)}")
            return None
    
    def _fetch_alpha_vantage_data(self) -> Optional[Dict[str, Any]]:
        """
        Fetch real-time data from Alpha Vantage API (mock implementation)
        """
        try:
            symbols = self.data_sources.get('symbols', [])
            
            # Mock Alpha Vantage data
            mock_data = {
                'source': 'alpha_vantage',
                'timestamp': datetime.utcnow().isoformat(),
                'tickers': []
            }
            
            for symbol in symbols:
                import random
                base_price = 10.5 if symbol == 'VIGL' else 8.5
                price = round(base_price * (1 + random.uniform(-0.03, 0.03)), 2)
                volume = random.randint(50000, 3000000)
                
                mock_data['tickers'].append({
                    'symbol': symbol,
                    'price': price,
                    'volume': volume,
                    'timestamp': datetime.utcnow().isoformat(),
                    'source': 'alpha_vantage_realtime'
                })
            
            logger.info(f"Fetched Alpha Vantage data for {len(symbols)} symbols")
            return mock_data
            
        except Exception as e:
            logger.error(f"Error fetching Alpha Vantage data: {str(e)}")
            return None
    
    def _validate_realtime_data(self, data: Dict[str, Any], source: str) -> Optional[Dict[str, Any]]:
        """
        Validate real-time market data
        """
        try:
            # Reset validation errors for this batch
            batch_errors = []
            
            if not self.validate_market_data(data):
                logger.warning(f"Market data validation failed for {source}")
                return None
            
            validated_tickers = []
            ticker_list = data.get('tickers', [])
            
            for ticker_data in ticker_list:
                # Store original validation errors count
                error_count_before = len(self.validation_errors)
                
                if self.validate_ticker_data(ticker_data):
                    # Apply quality rules
                    processed_ticker = self.apply_data_quality_rules(ticker_data.copy())
                    if processed_ticker:
                        processed_ticker['data_source'] = source
                        validated_tickers.append(processed_ticker)
                else:
                    # Collect errors for this batch
                    new_errors = self.validation_errors[error_count_before:]
                    batch_errors.extend(new_errors)
                    logger.warning(f"Real-time ticker validation failed: {ticker_data.get('symbol', 'unknown')}")
            
            if not validated_tickers:
                logger.warning(f"No valid tickers from {source}")
                return None
            
            return {
                'validation_timestamp': datetime.utcnow().isoformat(),
                'source': source,
                'input_count': len(ticker_list),
                'validated_count': len(validated_tickers),
                'validation_errors': batch_errors,
                'tickers': validated_tickers,
                'metadata': {
                    'agent': 'DataValidationAgent',
                    'version': '1.0.0',
                    'mode': 'realtime',
                    'data_source': source
                }
            }
            
        except Exception as e:
            logger.error(f"Error validating real-time data from {source}: {str(e)}")
            return None
    
    def _publish_validated_data(self, validated_data: Dict[str, Any]):
        """
        Publish validated real-time data to data store/message queue
        """
        try:
            # Write to real-time output file
            success = self._write_json_file(self.realtime_output_file, validated_data)
            
            if success:
                source = validated_data.get('source', 'unknown')
                count = validated_data.get('validated_count', 0)
                logger.info(f"Published {count} validated tickers from {source} to data store")
                
                # Also add to internal queue for other agents
                self.realtime_data_queue.put(validated_data)
            else:
                logger.error("Failed to publish validated data")
                
        except Exception as e:
            logger.error(f"Error publishing validated data: {str(e)}")
    
    def _send_confirmation(self, command_type: str, status: str, data: Dict[str, Any]):
        """
        Send confirmation to Orchestration Agent
        """
        try:
            confirmation_file = self.base_path / "confirmations.json"
            
            # Read existing confirmations
            confirmations = self._read_json_file(confirmation_file) or {'confirmations': []}
            
            # Add new confirmation
            confirmation = {
                'timestamp': datetime.utcnow().isoformat(),
                'agent': 'DataValidationAgent',
                'command_type': command_type,
                'status': status,
                'data': data
            }
            
            confirmations['confirmations'].append(confirmation)
            
            # Write back to file
            self._write_json_file(confirmation_file, confirmations)
            
            logger.info(f"Sent confirmation for {command_type}: {status}")
            
        except Exception as e:
            logger.error(f"Error sending confirmation: {str(e)}")
    
    def _stop_integration(self):
        """
        Stop real-time data integration
        """
        logger.info("Stopping real-time data integration")
        self.is_integrating = False
        
        # Send stop confirmation via message bus
        self.send_message_to_orchestrator({
            'status': 'realtime_integration_stopped',
            'command_type': 'STOP_INTEGRATION',
            'data': {
                'status': 'Real-time integration stopped successfully',
                'final_stats': {
                    'total_messages_processed': getattr(self, 'total_messages_processed', 0),
                    'integration_duration': getattr(self, 'integration_start_time', datetime.utcnow())
                }
            }
        })
        
        # Also send to legacy confirmation system
        self._send_confirmation('STOP_INTEGRATION', 'COMPLETED', {
            'status': 'Real-time integration stopped successfully'
        })
    
    def start_command_listener(self):
        """
        Start the command listener in a separate thread
        """
        if not self.is_listening:
            self.command_thread = threading.Thread(target=self.listen_for_commands)
            self.command_thread.daemon = True
            self.command_thread.start()
            logger.info("Command listener started")
    
    def stop_command_listener(self):
        """
        Stop the command listener
        """
        self.is_listening = False
        self.is_integrating = False
        if self.command_thread and self.command_thread.is_alive():
            self.command_thread.join(timeout=5)
        logger.info("Command listener stopped")
    
    def read_input_data(self) -> Optional[Dict[str, Any]]:
        """
        Read data from input file
        """
        try:
            if not self.input_file.exists():
                logger.error(f"Input file not found: {self.input_file}")
                return None
                
            with open(self.input_file, 'r') as f:
                data = json.load(f)
                logger.info(f"Successfully read input data from {self.input_file}")
                return data
                
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in input file: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Error reading input file: {str(e)}")
            return None
    
    def write_output_data(self, validated_data: Dict[str, Any]) -> bool:
        """
        Write validated data to output file
        """
        try:
            with open(self.output_file, 'w') as f:
                json.dump(validated_data, f, indent=2)
                logger.info(f"Successfully wrote validated data to {self.output_file}")
                return True
                
        except Exception as e:
            logger.error(f"Error writing output file: {str(e)}")
            return False
    
    def validate_and_process(self) -> bool:
        """
        Main validation and processing workflow
        """
        logger.info("Starting data validation process")
        self.validation_errors = []
        
        # Read input data
        raw_data = self.read_input_data()
        if raw_data is None:
            return False
            
        # Validate market data structure
        if not self.validate_market_data(raw_data):
            logger.error("Market data structure validation failed")
            logger.error(f"Validation errors: {self.validation_errors}")
            return False
            
        # Process ticker data
        ticker_list = raw_data.get('tickers', [])
        validated_tickers = []
        
        for ticker_data in ticker_list:
            if self.validate_ticker_data(ticker_data):
                # Apply quality rules and transformations
                processed_ticker = self.apply_data_quality_rules(ticker_data)
                if processed_ticker:
                    validated_tickers.append(processed_ticker)
            else:
                logger.warning(f"Ticker validation failed: {ticker_data.get('symbol', 'unknown')}")
        
        # Filter duplicates
        validated_tickers = self.filter_duplicates(validated_tickers)
        
        # Prepare output data
        validated_data = {
            'validation_timestamp': datetime.utcnow().isoformat(),
            'input_count': len(ticker_list),
            'validated_count': len(validated_tickers),
            'validation_errors': self.validation_errors[:100],  # Limit error list
            'tickers': validated_tickers,
            'metadata': {
                'agent': 'DataValidationAgent',
                'version': '1.0.0',
                'data_source': str(self.input_file)
            }
        }
        
        # Write validated data
        success = self.write_output_data(validated_data)
        
        if success:
            logger.info(f"Validation complete. Processed {len(ticker_list)} -> {len(validated_tickers)} tickers")
            if self.validation_errors:
                logger.warning(f"Encountered {len(self.validation_errors)} validation errors")
            
            # Send completion message to orchestrator
            self.send_message_to_orchestrator({
                'status': 'validation_completed',
                'data': {
                    'input_count': len(ticker_list),
                    'validated_count': len(validated_tickers),
                    'error_count': len(self.validation_errors),
                    'validation_errors': self.validation_errors[:10],  # First 10 errors
                    'output_file': str(self.output_file)
                }
            })
        else:
            # Send error message to orchestrator
            self.send_message_to_orchestrator({
                'status': 'validation_failed',
                'data': {
                    'error_count': len(self.validation_errors),
                    'validation_errors': self.validation_errors[:10]
                }
            })
        
        return success
    
    def get_validation_summary(self) -> Dict[str, Any]:
        """
        Get summary of validation results
        """
        return {
            'input_file': str(self.input_file),
            'output_file': str(self.output_file),
            'validation_errors_count': len(self.validation_errors),
            'last_run': datetime.utcnow().isoformat()
        }

def main():
    """
    Main entry point for the Data Validation Agent
    """
    agent = DataValidationAgent()
    
    try:
        # Check if running in real-time mode
        import sys
        if '--realtime' in sys.argv:
            logger.info("Starting Data Validation Agent in real-time mode")
            agent.start_command_listener()
            
            # Keep the agent running
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                logger.info("Shutting down Data Validation Agent")
                agent.stop_command_listener()
                return 0
        else:
            # Send startup message to orchestrator
            agent.send_message_to_orchestrator({
                'status': 'agent_started',
                'data': {
                    'mode': 'batch_validation',
                    'input_file': str(agent.input_file),
                    'output_file': str(agent.output_file)
                }
            })
            
            # Run batch validation
            success = agent.validate_and_process()
            
            if success:
                logger.info("Data validation completed successfully")
                summary = agent.get_validation_summary()
                logger.info(f"Validation summary: {json.dumps(summary, indent=2)}")
            else:
                logger.error("Data validation failed")
                return 1
            
    except Exception as e:
        logger.error(f"Unexpected error in data validation: {str(e)}")
        return 1
        
    return 0

if __name__ == "__main__":
    exit(main())
