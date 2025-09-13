"""
Enhanced Backtesting Agent for AMC-TRADER with Orchestration Integration

You are a Backtesting Agent responsible for:
1. Listening for VALIDATE_ALGORITHMS commands from Orchestration Agent
2. Retrieving latest discovery algorithms and parameters
3. Performing comprehensive backtesting simulations with multiple metrics
4. Analyzing results to identify algorithm weaknesses and optimization opportunities
5. Generating detailed validation reports with recommendations
6. Publishing results to data stores and confirming completion to Orchestration Agent

Enhanced capabilities include multi-strategy validation, real-time parameter retrieval,
statistical significance testing, and automated report generation.
"""

import json
import pandas as pd
import numpy as np
import time
import threading
import queue
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple, Callable
import logging
from dataclasses import dataclass, asdict
from pathlib import Path
import warnings
import hashlib
import requests
from enum import Enum
warnings.filterwarnings('ignore')

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    import pika
    PIKA_AVAILABLE = True
except ImportError:
    PIKA_AVAILABLE = False
    logger.warning("pika not available - RabbitMQ features will use file-based fallback")

class CommandType(Enum):
    VALIDATE_ALGORITHMS = "VALIDATE_ALGORITHMS"
    STATUS_CHECK = "STATUS_CHECK"
    SHUTDOWN = "SHUTDOWN"

class ValidationStatus(Enum):
    IDLE = "IDLE"
    PROCESSING = "PROCESSING" 
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

@dataclass
class Command:
    type: CommandType
    payload: Dict[str, Any]
    timestamp: datetime
    request_id: str

@dataclass
class BacktestResult:
    symbol: str
    entry_date: str
    entry_price: float
    exit_date: str
    exit_price: float
    return_pct: float
    holding_days: int
    max_drawdown: float
    peak_price: float
    strategy_score: float
    action_tag: str
    subscores: Dict[str, float] = None

@dataclass
class AlgorithmParameters:
    strategy: str
    weights: Dict[str, float]
    thresholds: Dict[str, Any]
    entry_rules: Dict[str, Any]
    version: str
    last_updated: datetime

@dataclass 
class ValidationReport:
    report_id: str
    timestamp: datetime
    algorithm_parameters: AlgorithmParameters
    performance_metrics: Dict[str, Any]
    backtest_results: List[BacktestResult]
    algorithm_analysis: Dict[str, Any]
    recommendations: List[str]
    statistical_significance: Dict[str, Any]
    risk_metrics: Dict[str, Any]
    status: ValidationStatus

class EnhancedBacktestingAgent:
    def __init__(self, data_dir: str = "../data", api_base_url: str = "https://amc-trader.onrender.com", 
                 rabbitmq_host: str = "localhost", orchestration_queue: str = "orchestration_queue"):
        self.data_dir = Path(data_dir)
        self.api_base_url = api_base_url
        self.rabbitmq_host = rabbitmq_host
        self.orchestration_queue = orchestration_queue
        self.discovery_file = self.data_dir / "discovery_results.json"
        self.results_file = self.data_dir / "backtesting_results.json"
        self.validation_reports_dir = self.data_dir / "validation_reports"
        self.command_queue = queue.Queue()
        self.status = ValidationStatus.IDLE
        self.current_report_id = None
        self.running = False
        self.ensure_data_directory()
        
        # Command callbacks
        self.command_handlers = {
            CommandType.VALIDATE_ALGORITHMS: self.handle_validate_algorithms,
            CommandType.STATUS_CHECK: self.handle_status_check,
            CommandType.SHUTDOWN: self.handle_shutdown
        }
        
    def ensure_data_directory(self):
        """Ensure data directories exist"""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.validation_reports_dir.mkdir(parents=True, exist_ok=True)
        
    # ============ MESSAGE BUS COMMUNICATION ============
    
    def send_message_to_orchestrator(self, message: Dict[str, Any]):
        """Send message to Orchestration Agent via RabbitMQ"""
        if not PIKA_AVAILABLE:
            logger.info("Using file-based messaging (pika not available)")
            self._fallback_file_message(message)
            return
            
        try:
            connection = pika.BlockingConnection(pika.ConnectionParameters(self.rabbitmq_host))
            channel = connection.channel()
            
            # Declare queue to ensure it exists
            channel.queue_declare(queue=self.orchestration_queue, durable=True)
            
            # Add agent identification to message
            message['agent_name'] = 'Backtesting Agent'
            message['timestamp'] = datetime.now().isoformat()
            
            # Publish message
            channel.basic_publish(
                exchange='',
                routing_key=self.orchestration_queue,
                body=json.dumps(message),
                properties=pika.BasicProperties(delivery_mode=2)  # Make message persistent
            )
            
            connection.close()
            logger.info(f"Message sent to Orchestration Agent: {message.get('status', 'unknown')}")
            
        except Exception as e:
            logger.warning(f"RabbitMQ connection failed: {e} - falling back to file-based communication")
            self._fallback_file_message(message)
            
    def _fallback_file_message(self, message: Dict[str, Any]):
        """Fallback method to save message to file when RabbitMQ unavailable"""
        try:
            message['agent_name'] = 'Backtesting Agent'
            message['timestamp'] = datetime.now().isoformat()
            
            fallback_file = self.data_dir / f"orchestrator_message_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(fallback_file, 'w') as f:
                json.dump(message, f, indent=2)
            logger.info(f"Message saved to fallback file: {fallback_file}")
        except Exception as e:
            logger.error(f"Failed to save fallback message: {e}")
            
    def send_status_update(self, status: str, details: Dict[str, Any] = None):
        """Send status update to Orchestration Agent"""
        message = {
            'message_type': 'status_update',
            'status': status,
            'current_report_id': self.current_report_id,
            'details': details or {}
        }
        self.send_message_to_orchestrator(message)
        
    def send_validation_started(self, request_id: str, strategies: List[str], parameters: Dict[str, Any]):
        """Send validation started notification"""
        message = {
            'message_type': 'validation_started',
            'status': 'validation_initiated',
            'request_id': request_id,
            'data': {
                'strategies': strategies,
                'parameters': parameters,
                'estimated_completion_minutes': len(strategies) * 2  # Rough estimate
            }
        }
        self.send_message_to_orchestrator(message)
        
    def send_validation_progress(self, request_id: str, progress_pct: float, current_step: str):
        """Send validation progress update"""
        message = {
            'message_type': 'validation_progress',
            'status': 'validation_in_progress',
            'request_id': request_id,
            'data': {
                'progress_percent': progress_pct,
                'current_step': current_step,
                'timestamp': datetime.now().isoformat()
            }
        }
        self.send_message_to_orchestrator(message)
        
    def send_validation_completed(self, request_id: str, report: ValidationReport):
        """Send validation completed notification with summary"""
        message = {
            'message_type': 'validation_completed',
            'status': 'validation_completed',
            'request_id': request_id,
            'data': {
                'report_id': report.report_id,
                'total_backtests': len(report.backtest_results),
                'win_rate': report.performance_metrics.get('win_rate', 0),
                'avg_return': report.performance_metrics.get('avg_return', 0),
                'sharpe_ratio': report.performance_metrics.get('sharpe_ratio', 0),
                'recommendations_count': len(report.recommendations),
                'algorithm_weaknesses_count': len(report.algorithm_analysis.get('algorithm_weaknesses', [])),
                'statistical_significance': report.statistical_significance.get('statistically_significant', False),
                'risk_rating': report.risk_metrics.get('risk_rating', 'Unknown'),
                'symbols_tested': list(set(r.symbol for r in report.backtest_results)) if report.backtest_results else [],
                'report_file_path': str(self.validation_reports_dir / f"{report.report_id}.json")
            }
        }
        self.send_message_to_orchestrator(message)
        
    def send_validation_failed(self, request_id: str, error_message: str):
        """Send validation failed notification"""
        message = {
            'message_type': 'validation_failed',
            'status': 'validation_failed',
            'request_id': request_id,
            'data': {
                'error_message': error_message,
                'timestamp': datetime.now().isoformat()
            }
        }
        self.send_message_to_orchestrator(message)
        
    def send_algorithm_weakness_alert(self, weaknesses: List[str], urgency: str = "medium"):
        """Send alert about discovered algorithm weaknesses"""
        message = {
            'message_type': 'algorithm_weakness_alert',
            'status': 'weakness_detected',
            'data': {
                'weaknesses': weaknesses,
                'urgency': urgency,
                'recommendation': 'Algorithm recalibration recommended' if len(weaknesses) > 2 else 'Monitor algorithm performance',
                'affected_components': self._extract_weak_components(weaknesses)
            }
        }
        self.send_message_to_orchestrator(message)
        
    def _extract_weak_components(self, weaknesses: List[str]) -> List[str]:
        """Extract component names from weakness descriptions"""
        components = []
        component_keywords = ['volume_momentum', 'squeeze', 'catalyst', 'options', 'technical']
        
        for weakness in weaknesses:
            for component in component_keywords:
                if component in weakness.lower():
                    components.append(component)
                    
        return list(set(components))
        
    # ============ ORCHESTRATION COMMAND HANDLING ============
    
    def start_listening(self):
        """Start the command listener thread"""
        self.running = True
        listener_thread = threading.Thread(target=self._command_listener, daemon=True)
        listener_thread.start()
        logger.info("Backtesting Agent started - listening for VALIDATE_ALGORITHMS commands")
        
    def stop_listening(self):
        """Stop the command listener"""
        self.running = False
        self.send_command(Command(
            type=CommandType.SHUTDOWN,
            payload={},
            timestamp=datetime.now(),
            request_id="internal_shutdown"
        ))
        
    def send_command(self, command: Command):
        """Send command to the agent"""
        self.command_queue.put(command)
        
    def _command_listener(self):
        """Main command processing loop"""
        while self.running:
            try:
                # Check for commands with timeout
                command = self.command_queue.get(timeout=1.0)
                logger.info(f"Received command: {command.type.value}")
                
                # Execute command handler
                if command.type in self.command_handlers:
                    self.command_handlers[command.type](command)
                else:
                    logger.warning(f"Unknown command type: {command.type}")
                    
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Error processing command: {e}")
                self.status = ValidationStatus.FAILED
                
    def handle_validate_algorithms(self, command: Command):
        """Handle VALIDATE_ALGORITHMS command from Orchestration Agent"""
        try:
            self.status = ValidationStatus.PROCESSING
            self.current_report_id = command.request_id
            
            logger.info(f"Starting algorithm validation - Request ID: {command.request_id}")
            
            # Extract validation parameters from command payload
            validation_params = command.payload
            strategies = validation_params.get('strategies', ['hybrid_v1'])
            holding_periods = validation_params.get('holding_periods', [5, 10])
            max_candidates = validation_params.get('max_candidates', 50)
            
            # Send validation started message to orchestrator
            self.send_validation_started(command.request_id, strategies, validation_params)
            
            # Send progress update
            self.send_validation_progress(command.request_id, 10.0, "Retrieving algorithm parameters")
            
            # Perform comprehensive validation
            validation_report = self.perform_comprehensive_validation(
                strategies=strategies,
                holding_periods=holding_periods,
                max_candidates=max_candidates,
                request_id=command.request_id
            )
            
            # Send progress update
            self.send_validation_progress(command.request_id, 90.0, "Generating validation report")
            
            # Save and publish results
            self._publish_validation_report(validation_report)
            self._send_confirmation_to_orchestration(command.request_id, "SUCCESS", validation_report)
            
            # Send completion message to orchestrator
            self.send_validation_completed(command.request_id, validation_report)
            
            # Check for algorithm weaknesses and send alerts if necessary
            weaknesses = validation_report.algorithm_analysis.get('algorithm_weaknesses', [])
            if weaknesses:
                urgency = "high" if len(weaknesses) > 3 else "medium"
                self.send_algorithm_weakness_alert(weaknesses, urgency)
            
            self.status = ValidationStatus.COMPLETED
            logger.info(f"Algorithm validation completed - Report ID: {validation_report.report_id}")
            
        except Exception as e:
            logger.error(f"Algorithm validation failed: {e}")
            self.status = ValidationStatus.FAILED
            self._send_confirmation_to_orchestration(command.request_id, "FAILED", None, str(e))
            self.send_validation_failed(command.request_id, str(e))
            
    def handle_status_check(self, command: Command):
        """Handle status check requests"""
        status_info = {
            'status': self.status.value,
            'current_report_id': self.current_report_id,
            'timestamp': datetime.now().isoformat()
        }
        logger.info(f"Status check: {status_info}")
        return status_info
        
    def handle_shutdown(self, command: Command):
        """Handle shutdown command"""
        logger.info("Received shutdown command")
        self.running = False
        
    # ============ ALGORITHM PARAMETER RETRIEVAL ============
        
    def retrieve_current_algorithm_parameters(self, strategy: str = "hybrid_v1") -> AlgorithmParameters:
        """Retrieve current algorithm parameters from API or configuration"""
        try:
            # Try to get parameters from API first
            response = requests.get(f"{self.api_base_url}/discovery/calibration/{strategy}/config", timeout=10)
            if response.status_code == 200:
                config_data = response.json()
                return AlgorithmParameters(
                    strategy=strategy,
                    weights=config_data.get('weights', {}),
                    thresholds=config_data.get('thresholds', {}),
                    entry_rules=config_data.get('entry_rules', {}),
                    version=config_data.get('version', '1.0'),
                    last_updated=datetime.now()
                )
        except Exception as e:
            logger.warning(f"Failed to retrieve parameters from API: {e}")
            
        # Fallback to default parameters
        logger.info("Using default algorithm parameters")
        return AlgorithmParameters(
            strategy=strategy,
            weights={
                "volume_momentum": 0.35,
                "squeeze": 0.25,
                "catalyst": 0.20,
                "options": 0.10,
                "technical": 0.10
            },
            thresholds={
                "min_relvol_30": 2.5,
                "min_atr_pct": 0.04,
                "rsi_band": [60, 70],
                "require_vwap_reclaim": True
            },
            entry_rules={
                "watchlist_min": 70,
                "trade_ready_min": 75
            },
            version="1.0_default",
            last_updated=datetime.now()
        )
        
    def fetch_discovery_candidates(self, strategy: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Fetch fresh discovery candidates from API"""
        try:
            response = requests.get(
                f"{self.api_base_url}/discovery/contenders",
                params={"strategy": strategy, "limit": limit},
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get('candidates', [])
            else:
                logger.warning(f"API returned status {response.status_code}")
                
        except Exception as e:
            logger.error(f"Failed to fetch discovery candidates: {e}")
            
        # Fallback to local file
        return self.load_discovery_results()
        
    # ============ COMPREHENSIVE VALIDATION ============
        
    def perform_comprehensive_validation(self, strategies: List[str], holding_periods: List[int], 
                                       max_candidates: int, request_id: str) -> ValidationReport:
        """Perform comprehensive multi-strategy algorithm validation"""
        logger.info(f"Starting comprehensive validation for strategies: {strategies}")
        
        all_results = []
        algorithm_params = {}
        total_steps = len(strategies) * (1 + len(holding_periods)) + 3  # +3 for analysis steps
        current_step = 0
        
        for strategy_idx, strategy in enumerate(strategies):
            logger.info(f"Validating strategy: {strategy}")
            
            # Send progress update
            progress = (current_step / total_steps) * 80 + 20  # 20-100% range
            self.send_validation_progress(request_id, progress, f"Processing strategy: {strategy}")
            current_step += 1
            
            # Retrieve algorithm parameters
            params = self.retrieve_current_algorithm_parameters(strategy)
            algorithm_params[strategy] = params
            
            # Get discovery candidates
            candidates = self.fetch_discovery_candidates(strategy, max_candidates)
            logger.info(f"Found {len(candidates)} candidates for {strategy}")
            
            if not candidates:
                continue
                
            # Run backtests for multiple holding periods
            for holding_period in holding_periods:
                progress = (current_step / total_steps) * 80 + 20
                self.send_validation_progress(request_id, progress, 
                    f"Backtesting {strategy} with {holding_period}-day holding period")
                
                strategy_results = self._run_enhanced_backtest(candidates, holding_period, strategy)
                all_results.extend(strategy_results)
                current_step += 1
                
        # Generate comprehensive analysis
        self.send_validation_progress(request_id, 85.0, "Calculating performance metrics")
        performance_metrics = self._calculate_enhanced_performance_metrics(all_results)
        
        self.send_validation_progress(request_id, 90.0, "Analyzing algorithm effectiveness")
        algorithm_analysis = self._analyze_algorithm_effectiveness(all_results, algorithm_params)
        
        self.send_validation_progress(request_id, 95.0, "Generating recommendations and risk analysis")
        recommendations = self._generate_optimization_recommendations(algorithm_analysis, performance_metrics)
        statistical_significance = self._calculate_statistical_significance(all_results)
        risk_metrics = self._calculate_risk_metrics(all_results)
        
        # Create validation report
        report = ValidationReport(
            report_id=f"validation_{request_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            timestamp=datetime.now(),
            algorithm_parameters=algorithm_params.get(strategies[0]) if strategies else None,
            performance_metrics=performance_metrics,
            backtest_results=all_results,
            algorithm_analysis=algorithm_analysis,
            recommendations=recommendations,
            statistical_significance=statistical_significance,
            risk_metrics=risk_metrics,
            status=ValidationStatus.COMPLETED
        )
        
        return report
        
    # ============ ENHANCED BACKTESTING METHODS ============
        
    def _run_enhanced_backtest(self, candidates: List[Dict[str, Any]], holding_days: int, strategy: str) -> List[BacktestResult]:
        """Run enhanced backtesting with comprehensive metrics"""
        results = []
        
        for i, candidate in enumerate(candidates):
            symbol = candidate.get('symbol', '')
            score = candidate.get('score', 0)
            action_tag = candidate.get('action_tag', 'unknown')
            subscores = candidate.get('subscores', {})
            
            # Mock enhanced backtesting (replace with real yfinance in production)
            mock_result = self._create_mock_backtest_result(symbol, score, action_tag, subscores, holding_days, strategy)
            if mock_result:
                results.append(mock_result)
                
        logger.info(f"Completed backtesting for {len(results)} candidates with {holding_days}-day holding period")
        return results
        
    def _create_mock_backtest_result(self, symbol: str, score: float, action_tag: str, 
                                   subscores: Dict[str, float], holding_days: int, strategy: str) -> BacktestResult:
        """Create mock backtest result for demonstration (replace with real data)"""
        # Mock performance calculation based on score and subscores
        base_return = (score - 70) * 0.3
        volume_bonus = subscores.get('volume_momentum', 0.5) * 10
        squeeze_bonus = subscores.get('squeeze', 0.5) * 8
        catalyst_bonus = subscores.get('catalyst', 0.5) * 6
        
        # Add some randomness for realistic results
        symbol_hash = abs(hash(symbol)) % 100
        random_factor = (symbol_hash - 50) * 0.1
        
        total_return = base_return + volume_bonus + squeeze_bonus + catalyst_bonus + random_factor
        
        # Mock risk metrics
        max_drawdown = abs(total_return) * 0.4
        
        return BacktestResult(
            symbol=symbol,
            entry_date="2025-01-10",
            entry_price=100.0,
            exit_date="2025-01-15",
            exit_price=100.0 + total_return,
            return_pct=round(total_return, 2),
            holding_days=holding_days,
            max_drawdown=round(max_drawdown, 2),
            peak_price=100.0 + max(0, total_return * 1.2),
            strategy_score=round(score, 2),
            action_tag=action_tag,
            subscores=subscores
        )
        
    def _calculate_enhanced_performance_metrics(self, results: List[BacktestResult]) -> Dict[str, Any]:
        """Calculate comprehensive performance metrics"""
        if not results:
            return {}
            
        returns = [r.return_pct for r in results]
        
        # Basic metrics
        total_trades = len(results)
        winning_trades = len([r for r in results if r.return_pct > 0])
        win_rate = (winning_trades / total_trades) * 100 if total_trades > 0 else 0
        
        # Return statistics
        avg_return = np.mean(returns)
        median_return = np.median(returns)
        std_return = np.std(returns)
        sharpe_ratio = (avg_return / std_return) if std_return > 0 else 0
        
        # Advanced metrics
        downside_returns = [r for r in returns if r < 0]
        downside_std = np.std(downside_returns) if downside_returns else 0
        sortino_ratio = (avg_return / downside_std) if downside_std > 0 else 0
        
        # Percentile analysis
        percentiles = {
            'p25': np.percentile(returns, 25),
            'p50': np.percentile(returns, 50), 
            'p75': np.percentile(returns, 75),
            'p90': np.percentile(returns, 90)
        }
        
        # Action tag performance
        action_tag_performance = {}
        for tag in set(r.action_tag for r in results):
            tag_results = [r for r in results if r.action_tag == tag]
            if tag_results:
                tag_returns = [r.return_pct for r in tag_results]
                action_tag_performance[tag] = {
                    'count': len(tag_results),
                    'avg_return': round(np.mean(tag_returns), 2),
                    'win_rate': round(len([r for r in tag_results if r.return_pct > 0]) / len(tag_results) * 100, 2),
                    'best_return': round(max(tag_returns), 2),
                    'worst_return': round(min(tag_returns), 2)
                }
                
        return {
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'losing_trades': total_trades - winning_trades,
            'win_rate': round(win_rate, 2),
            'avg_return': round(avg_return, 2),
            'median_return': round(median_return, 2),
            'std_return': round(std_return, 2),
            'sharpe_ratio': round(sharpe_ratio, 3),
            'sortino_ratio': round(sortino_ratio, 3),
            'percentiles': {k: round(v, 2) for k, v in percentiles.items()},
            'best_trade_return': round(max(returns), 2) if returns else 0,
            'worst_trade_return': round(min(returns), 2) if returns else 0,
            'action_tag_performance': action_tag_performance
        }
        
    def load_discovery_results(self) -> List[Dict[str, Any]]:
        """Load discovery results from JSON file"""
        try:
            if not self.discovery_file.exists():
                logger.warning(f"Discovery results file not found: {self.discovery_file}")
                return []
                
            with open(self.discovery_file, 'r') as f:
                data = json.load(f)
                return data.get('candidates', [])
        except Exception as e:
            logger.error(f"Error loading discovery results: {e}")
            return []
    
    def get_historical_data(self, symbol: str, start_date: str, days_ahead: int = 30) -> Optional[pd.DataFrame]:
        """Fetch historical price data for a symbol"""
        try:
            start = pd.to_datetime(start_date)
            end = start + timedelta(days=days_ahead + 10)  # Buffer for weekends/holidays
            
            ticker = yf.Ticker(symbol)
            hist = ticker.history(start=start.strftime('%Y-%m-%d'), 
                                end=end.strftime('%Y-%m-%d'))
            
            if hist.empty:
                logger.warning(f"No historical data found for {symbol}")
                return None
                
            return hist
        except Exception as e:
            logger.error(f"Error fetching data for {symbol}: {e}")
            return None
    
    def simulate_trade(self, symbol: str, entry_date: str, strategy_score: float, 
                      action_tag: str, holding_days: int = 5) -> Optional[BacktestResult]:
        """Simulate a trade for backtesting"""
        hist_data = self.get_historical_data(symbol, entry_date, holding_days + 5)
        
        if hist_data is None or len(hist_data) < 2:
            return None
            
        try:
            # Find entry price (next trading day after discovery)
            entry_idx = 1 if len(hist_data) > 1 else 0
            entry_price = hist_data.iloc[entry_idx]['Open']
            actual_entry_date = hist_data.index[entry_idx].strftime('%Y-%m-%d')
            
            # Find exit price (after holding period)
            exit_idx = min(entry_idx + holding_days, len(hist_data) - 1)
            exit_price = hist_data.iloc[exit_idx]['Close']
            actual_exit_date = hist_data.index[exit_idx].strftime('%Y-%m-%d')
            
            # Calculate performance metrics
            return_pct = ((exit_price - entry_price) / entry_price) * 100
            
            # Calculate max drawdown during holding period
            holding_period = hist_data.iloc[entry_idx:exit_idx + 1]
            peak_price = holding_period['High'].max()
            trough_price = holding_period['Low'].min()
            max_drawdown = ((trough_price - peak_price) / peak_price) * 100 if peak_price > 0 else 0
            
            actual_holding_days = (pd.to_datetime(actual_exit_date) - pd.to_datetime(actual_entry_date)).days
            
            return BacktestResult(
                symbol=symbol,
                entry_date=actual_entry_date,
                entry_price=float(entry_price),
                exit_date=actual_exit_date,
                exit_price=float(exit_price),
                return_pct=float(return_pct),
                holding_days=actual_holding_days,
                max_drawdown=float(max_drawdown),
                peak_price=float(peak_price),
                strategy_score=float(strategy_score),
                action_tag=action_tag
            )
            
        except Exception as e:
            logger.error(f"Error simulating trade for {symbol}: {e}")
            return None
    
    def calculate_performance_metrics(self, results: List[BacktestResult]) -> Dict[str, Any]:
        """Calculate overall portfolio performance metrics"""
        if not results:
            return {}
            
        returns = [r.return_pct for r in results]
        scores = [r.strategy_score for r in results]
        
        # Basic performance metrics
        total_trades = len(results)
        winning_trades = len([r for r in results if r.return_pct > 0])
        losing_trades = len([r for r in results if r.return_pct < 0])
        win_rate = (winning_trades / total_trades) * 100 if total_trades > 0 else 0
        
        # Return statistics
        avg_return = np.mean(returns)
        median_return = np.median(returns)
        std_return = np.std(returns)
        sharpe_ratio = (avg_return / std_return) if std_return > 0 else 0
        
        # Best and worst trades
        best_trade = max(results, key=lambda x: x.return_pct) if results else None
        worst_trade = min(results, key=lambda x: x.return_pct) if results else None
        
        # Score correlation analysis
        score_return_correlation = np.corrcoef(scores, returns)[0, 1] if len(scores) > 1 else 0
        
        # Action tag analysis
        action_tag_performance = {}
        for tag in set(r.action_tag for r in results):
            tag_results = [r for r in results if r.action_tag == tag]
            if tag_results:
                tag_returns = [r.return_pct for r in tag_results]
                action_tag_performance[tag] = {
                    'count': len(tag_results),
                    'avg_return': np.mean(tag_returns),
                    'win_rate': len([r for r in tag_results if r.return_pct > 0]) / len(tag_results) * 100
                }
        
        return {
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'win_rate': round(win_rate, 2),
            'avg_return': round(avg_return, 2),
            'median_return': round(median_return, 2),
            'std_return': round(std_return, 2),
            'sharpe_ratio': round(sharpe_ratio, 2),
            'best_trade': {
                'symbol': best_trade.symbol,
                'return_pct': round(best_trade.return_pct, 2),
                'score': round(best_trade.strategy_score, 2)
            } if best_trade else None,
            'worst_trade': {
                'symbol': worst_trade.symbol,
                'return_pct': round(worst_trade.return_pct, 2),
                'score': round(worst_trade.strategy_score, 2)
            } if worst_trade else None,
            'score_return_correlation': round(score_return_correlation, 3),
            'action_tag_performance': action_tag_performance
        }
    
    def analyze_strategy_effectiveness(self, results: List[BacktestResult]) -> Dict[str, Any]:
        """Analyze the effectiveness of different strategy components"""
        if not results:
            return {}
            
        # Score range analysis
        score_ranges = {
            'high_score_90+': [r for r in results if r.strategy_score >= 90],
            'good_score_80-90': [r for r in results if 80 <= r.strategy_score < 90],
            'medium_score_70-80': [r for r in results if 70 <= r.strategy_score < 80],
            'low_score_<70': [r for r in results if r.strategy_score < 70]
        }
        
        range_analysis = {}
        for range_name, range_results in score_ranges.items():
            if range_results:
                returns = [r.return_pct for r in range_results]
                range_analysis[range_name] = {
                    'count': len(range_results),
                    'avg_return': round(np.mean(returns), 2),
                    'win_rate': round(len([r for r in range_results if r.return_pct > 0]) / len(range_results) * 100, 2)
                }
        
        # Holding period analysis
        holding_periods = {}
        for result in results:
            period_key = f"{result.holding_days}_days"
            if period_key not in holding_periods:
                holding_periods[period_key] = []
            holding_periods[period_key].append(result.return_pct)
        
        period_analysis = {}
        for period, returns in holding_periods.items():
            period_analysis[period] = {
                'count': len(returns),
                'avg_return': round(np.mean(returns), 2),
                'win_rate': round(len([r for r in returns if r > 0]) / len(returns) * 100, 2)
            }
        
        return {
            'score_range_analysis': range_analysis,
            'holding_period_analysis': period_analysis,
            'insights': self.generate_insights(results)
        }
    
    def generate_insights(self, results: List[BacktestResult]) -> List[str]:
        """Generate actionable insights from backtesting results"""
        insights = []
        
        if not results:
            return ["No backtesting results available for analysis"]
        
        # Win rate insights
        win_rate = len([r for r in results if r.return_pct > 0]) / len(results) * 100
        if win_rate > 60:
            insights.append(f"Strong win rate of {win_rate:.1f}% indicates good strategy effectiveness")
        elif win_rate < 40:
            insights.append(f"Low win rate of {win_rate:.1f}% suggests strategy needs refinement")
        
        # Score correlation insights
        scores = [r.strategy_score for r in results]
        returns = [r.return_pct for r in results]
        correlation = np.corrcoef(scores, returns)[0, 1] if len(scores) > 1 else 0
        
        if correlation > 0.3:
            insights.append(f"Strong positive correlation ({correlation:.2f}) between strategy scores and returns")
        elif correlation < 0:
            insights.append(f"Negative correlation ({correlation:.2f}) suggests strategy scoring may need adjustment")
        
        # Action tag insights
        action_tags = set(r.action_tag for r in results)
        for tag in action_tags:
            tag_results = [r for r in results if r.action_tag == tag]
            tag_returns = [r.return_pct for r in tag_results]
            avg_return = np.mean(tag_returns)
            
            if avg_return > 5:
                insights.append(f"'{tag}' tagged stocks show strong average return of {avg_return:.1f}%")
            elif avg_return < -2:
                insights.append(f"'{tag}' tagged stocks underperforming with {avg_return:.1f}% average return")
        
        return insights
    
    def run_backtest(self, holding_days: int = 5, max_symbols: int = 50) -> Dict[str, Any]:
        """Run complete backtesting analysis"""
        logger.info("Starting backtesting analysis...")
        
        # Load discovery results
        discovery_results = self.load_discovery_results()
        if not discovery_results:
            logger.warning("No discovery results found for backtesting")
            return {"error": "No discovery results available"}
        
        # Limit symbols for practical backtesting
        discovery_results = discovery_results[:max_symbols]
        logger.info(f"Running backtest on {len(discovery_results)} symbols")
        
        # Simulate trades
        backtest_results = []
        for i, candidate in enumerate(discovery_results):
            logger.info(f"Processing {i+1}/{len(discovery_results)}: {candidate.get('symbol', 'Unknown')}")
            
            result = self.simulate_trade(
                symbol=candidate.get('symbol', ''),
                entry_date=candidate.get('discovery_date', ''),
                strategy_score=candidate.get('score', 0),
                action_tag=candidate.get('action_tag', 'unknown'),
                holding_days=holding_days
            )
            
            if result:
                backtest_results.append(result)
        
        logger.info(f"Successfully backtested {len(backtest_results)} trades")
        
        # Calculate performance metrics
        performance_metrics = self.calculate_performance_metrics(backtest_results)
        strategy_analysis = self.analyze_strategy_effectiveness(backtest_results)
        
        # Compile final results
        final_results = {
            'metadata': {
                'backtest_date': datetime.now().isoformat(),
                'total_candidates_analyzed': len(discovery_results),
                'successful_backtests': len(backtest_results),
                'holding_period_days': holding_days,
                'data_source': 'yfinance'
            },
            'performance_metrics': performance_metrics,
            'strategy_analysis': strategy_analysis,
            'individual_trades': [
                {
                    'symbol': r.symbol,
                    'entry_date': r.entry_date,
                    'exit_date': r.exit_date,
                    'return_pct': round(r.return_pct, 2),
                    'holding_days': r.holding_days,
                    'strategy_score': round(r.strategy_score, 2),
                    'action_tag': r.action_tag,
                    'max_drawdown': round(r.max_drawdown, 2)
                }
                for r in backtest_results
            ]
        }
        
        return final_results
    
    def save_results(self, results: Dict[str, Any]) -> bool:
        """Save backtesting results to JSON file"""
        try:
            with open(self.results_file, 'w') as f:
                json.dump(results, f, indent=2)
            logger.info(f"Backtesting results saved to {self.results_file}")
            return True
        except Exception as e:
            logger.error(f"Error saving results: {e}")
            return False
    
    def execute(self, holding_days: int = 5, max_symbols: int = 30) -> bool:
        """Execute the complete backtesting workflow"""
        try:
            logger.info("Backtesting Agent starting execution...")
            
            # Run backtest
            results = self.run_backtest(holding_days=holding_days, max_symbols=max_symbols)
            
            if 'error' in results:
                logger.error(f"Backtesting failed: {results['error']}")
                return False
            
            # Save results
            success = self.save_results(results)
            
            if success:
                # Log summary
                metrics = results.get('performance_metrics', {})
                logger.info(f"Backtesting completed successfully:")
                logger.info(f"  - Total trades: {metrics.get('total_trades', 0)}")
                logger.info(f"  - Win rate: {metrics.get('win_rate', 0)}%")
                logger.info(f"  - Average return: {metrics.get('avg_return', 0)}%")
                logger.info(f"  - Sharpe ratio: {metrics.get('sharpe_ratio', 0)}")
                
                return True
            else:
                return False
                
        except Exception as e:
            logger.error(f"Error in backtesting execution: {e}")
            return False

    # ============ ALGORITHM ANALYSIS METHODS ============
        
    def _analyze_algorithm_effectiveness(self, results: List[BacktestResult], algorithm_params: Dict[str, AlgorithmParameters]) -> Dict[str, Any]:
        """Analyze algorithm effectiveness and identify weaknesses"""
        if not results:
            return {}
            
        analysis = {}
        
        # Score correlation analysis
        scores = [r.strategy_score for r in results]
        returns = [r.return_pct for r in results]
        score_correlation = np.corrcoef(scores, returns)[0, 1] if len(scores) > 1 else 0
        
        # Subscore effectiveness analysis
        subscore_analysis = {}
        for subscore_name in ['volume_momentum', 'squeeze', 'catalyst', 'options', 'technical']:
            subscore_values = []
            subscore_returns = []
            
            for result in results:
                if result.subscores and subscore_name in result.subscores:
                    subscore_values.append(result.subscores[subscore_name])
                    subscore_returns.append(result.return_pct)
                    
            if len(subscore_values) > 1:
                correlation = np.corrcoef(subscore_values, subscore_returns)[0, 1]
                subscore_analysis[subscore_name] = {
                    'correlation_with_returns': round(correlation, 3),
                    'avg_subscore': round(np.mean(subscore_values), 3),
                    'effectiveness_rating': 'High' if correlation > 0.3 else 'Medium' if correlation > 0.1 else 'Low'
                }
        
        # Action tag effectiveness
        tag_effectiveness = {}
        for tag in set(r.action_tag for r in results):
            tag_results = [r for r in results if r.action_tag == tag]
            if tag_results:
                tag_returns = [r.return_pct for r in tag_results]
                tag_effectiveness[tag] = {
                    'count': len(tag_results),
                    'avg_return': round(np.mean(tag_returns), 2),
                    'win_rate': round(len([r for r in tag_results if r.return_pct > 0]) / len(tag_results) * 100, 2),
                    'effectiveness': 'Strong' if np.mean(tag_returns) > 2 else 'Moderate' if np.mean(tag_returns) > 0 else 'Weak'
                }
        
        # Score threshold analysis
        score_thresholds = {
            'high_confidence_85+': [r for r in results if r.strategy_score >= 85],
            'good_confidence_75-85': [r for r in results if 75 <= r.strategy_score < 85],
            'moderate_confidence_70-75': [r for r in results if 70 <= r.strategy_score < 75],
            'low_confidence_<70': [r for r in results if r.strategy_score < 70]
        }
        
        threshold_analysis = {}
        for threshold_name, threshold_results in score_thresholds.items():
            if threshold_results:
                threshold_returns = [r.return_pct for r in threshold_results]
                threshold_analysis[threshold_name] = {
                    'count': len(threshold_results),
                    'avg_return': round(np.mean(threshold_returns), 2),
                    'win_rate': round(len([r for r in threshold_results if r.return_pct > 0]) / len(threshold_results) * 100, 2)
                }
        
        analysis = {
            'overall_score_correlation': round(score_correlation, 3),
            'subscore_effectiveness': subscore_analysis,
            'action_tag_effectiveness': tag_effectiveness,
            'score_threshold_analysis': threshold_analysis,
            'algorithm_weaknesses': self._identify_algorithm_weaknesses(subscore_analysis, tag_effectiveness, score_correlation)
        }
        
        return analysis
        
    def _identify_algorithm_weaknesses(self, subscore_analysis: Dict[str, Any], tag_effectiveness: Dict[str, Any], score_correlation: float) -> List[str]:
        """Identify specific algorithm weaknesses and improvement areas"""
        weaknesses = []
        
        # Check overall correlation
        if score_correlation < 0.2:
            weaknesses.append("Low correlation between strategy scores and actual returns suggests scoring algorithm needs calibration")
            
        # Check subscore effectiveness
        weak_subscores = [name for name, data in subscore_analysis.items() 
                         if data.get('effectiveness_rating') == 'Low']
        if weak_subscores:
            weaknesses.append(f"Weak performing subscores need improvement: {', '.join(weak_subscores)}")
            
        # Check action tag performance
        weak_tags = [tag for tag, data in tag_effectiveness.items() 
                    if data.get('effectiveness') == 'Weak']
        if weak_tags:
            weaknesses.append(f"Action tags showing poor performance: {', '.join(weak_tags)}")
            
        # Check for overfitting to high scores
        high_score_data = subscore_analysis.get('high_confidence_85+', {})
        if high_score_data.get('count', 0) > 0 and high_score_data.get('avg_return', 0) < 2:
            weaknesses.append("High-confidence picks underperforming - possible overfitting to technical indicators")
            
        return weaknesses
        
    def _generate_optimization_recommendations(self, algorithm_analysis: Dict[str, Any], performance_metrics: Dict[str, Any]) -> List[str]:
        """Generate specific recommendations for algorithm optimization"""
        recommendations = []
        
        # Performance-based recommendations
        win_rate = performance_metrics.get('win_rate', 0)
        avg_return = performance_metrics.get('avg_return', 0)
        sharpe_ratio = performance_metrics.get('sharpe_ratio', 0)
        
        if win_rate < 55:
            recommendations.append("Consider tightening entry criteria - current win rate below 55% threshold")
            
        if avg_return < 2:
            recommendations.append("Explore higher conviction scoring - average returns below 2% target")
            
        if sharpe_ratio < 0.5:
            recommendations.append("Improve risk-adjusted returns - implement better risk management in scoring")
            
        # Subscore-based recommendations
        subscore_effectiveness = algorithm_analysis.get('subscore_effectiveness', {})
        
        for subscore, data in subscore_effectiveness.items():
            if data.get('effectiveness_rating') == 'Low':
                if subscore == 'catalyst':
                    recommendations.append("Enhance catalyst detection - consider real-time news sentiment analysis")
                elif subscore == 'squeeze':
                    recommendations.append("Refine squeeze scoring - evaluate short interest and float calculations")
                elif subscore == 'volume_momentum':
                    recommendations.append("Optimize volume analysis - consider intraday volume patterns")
                elif subscore == 'options':
                    recommendations.append("Improve options flow analysis - integrate gamma exposure metrics")
                elif subscore == 'technical':
                    recommendations.append("Review technical indicators - consider additional momentum signals")
                    
        # Action tag recommendations
        tag_effectiveness = algorithm_analysis.get('action_tag_effectiveness', {})
        
        if 'trade_ready' in tag_effectiveness:
            trade_ready_performance = tag_effectiveness['trade_ready']
            if trade_ready_performance.get('avg_return', 0) < 3:
                recommendations.append("Raise 'trade_ready' threshold - current performance below expectations")
                
        # Algorithm weakness recommendations
        weaknesses = algorithm_analysis.get('algorithm_weaknesses', [])
        if len(weaknesses) > 2:
            recommendations.append("Consider comprehensive algorithm recalibration - multiple weaknesses identified")
            
        return recommendations
        
    def _calculate_statistical_significance(self, results: List[BacktestResult]) -> Dict[str, Any]:
        """Calculate statistical significance of backtesting results"""
        if not results:
            return {}
            
        returns = [r.return_pct for r in results]
        n_trades = len(returns)
        
        # T-test against zero (no performance)
        if n_trades > 1:
            avg_return = np.mean(returns)
            std_return = np.std(returns, ddof=1)
            t_stat = (avg_return * np.sqrt(n_trades)) / std_return if std_return > 0 else 0
            
            # Simple significance test (normally would use scipy.stats)
            significant = abs(t_stat) > 2.0  # Rough approximation for p < 0.05
            
            return {
                'sample_size': n_trades,
                'mean_return': round(avg_return, 3),
                'std_error': round(std_return / np.sqrt(n_trades), 3),
                't_statistic': round(t_stat, 3),
                'statistically_significant': significant,
                'confidence_level': 'High' if abs(t_stat) > 2.5 else 'Medium' if abs(t_stat) > 1.5 else 'Low'
            }
            
        return {'sample_size': n_trades, 'note': 'Insufficient data for significance testing'}
        
    def _calculate_risk_metrics(self, results: List[BacktestResult]) -> Dict[str, Any]:
        """Calculate comprehensive risk metrics"""
        if not results:
            return {}
            
        returns = [r.return_pct for r in results]
        drawdowns = [r.max_drawdown for r in results]
        
        # Value at Risk (95% confidence)
        var_95 = np.percentile(returns, 5)
        
        # Maximum drawdown
        max_dd = max(drawdowns) if drawdowns else 0
        avg_dd = np.mean(drawdowns) if drawdowns else 0
        
        # Volatility metrics
        volatility = np.std(returns)
        
        # Downside deviation
        negative_returns = [r for r in returns if r < 0]
        downside_deviation = np.std(negative_returns) if negative_returns else 0
        
        return {
            'value_at_risk_95': round(var_95, 2),
            'max_drawdown': round(max_dd, 2),
            'avg_drawdown': round(avg_dd, 2),
            'volatility': round(volatility, 2),
            'downside_deviation': round(downside_deviation, 2),
            'risk_rating': 'High' if volatility > 5 else 'Medium' if volatility > 3 else 'Low'
        }
        
    # ============ REPORT PUBLISHING AND CONFIRMATION ============
        
    def _publish_validation_report(self, report: ValidationReport):
        """Publish validation report to data store"""
        try:
            # Save to file system
            report_file = self.validation_reports_dir / f"{report.report_id}.json"
            
            # Convert report to dict for JSON serialization
            report_dict = {
                'report_id': report.report_id,
                'timestamp': report.timestamp.isoformat(),
                'algorithm_parameters': {
                    'strategy': report.algorithm_parameters.strategy if report.algorithm_parameters else 'unknown',
                    'weights': report.algorithm_parameters.weights if report.algorithm_parameters else {},
                    'thresholds': report.algorithm_parameters.thresholds if report.algorithm_parameters else {},
                    'entry_rules': report.algorithm_parameters.entry_rules if report.algorithm_parameters else {},
                    'version': report.algorithm_parameters.version if report.algorithm_parameters else 'unknown'
                },
                'performance_metrics': report.performance_metrics,
                'algorithm_analysis': report.algorithm_analysis,
                'recommendations': report.recommendations,
                'statistical_significance': report.statistical_significance,
                'risk_metrics': report.risk_metrics,
                'status': report.status.value,
                'backtest_summary': {
                    'total_backtests': len(report.backtest_results),
                    'symbols_tested': list(set(r.symbol for r in report.backtest_results)),
                    'avg_holding_period': np.mean([r.holding_days for r in report.backtest_results]) if report.backtest_results else 0
                }
            }
            
            with open(report_file, 'w') as f:
                json.dump(report_dict, f, indent=2)
                
            logger.info(f"Validation report published to: {report_file}")
            
            # Also update the main backtesting results file for compatibility
            self.save_results({
                'metadata': {
                    'backtest_date': report.timestamp.isoformat(),
                    'report_id': report.report_id,
                    'validation_type': 'comprehensive_algorithm_validation'
                },
                'performance_metrics': report.performance_metrics,
                'algorithm_analysis': report.algorithm_analysis,
                'recommendations': report.recommendations,
                'statistical_significance': report.statistical_significance,
                'risk_metrics': report.risk_metrics
            })
            
        except Exception as e:
            logger.error(f"Failed to publish validation report: {e}")
            raise
            
    def _send_confirmation_to_orchestration(self, request_id: str, status: str, report: Optional[ValidationReport], error_message: str = None):
        """Send confirmation to Orchestration Agent"""
        confirmation = {
            'request_id': request_id,
            'agent': 'BacktestingAgent',
            'command': 'VALIDATE_ALGORITHMS',
            'status': status,
            'timestamp': datetime.now().isoformat(),
            'report_id': report.report_id if report else None,
            'summary': {
                'total_backtests': len(report.backtest_results) if report and report.backtest_results else 0,
                'win_rate': report.performance_metrics.get('win_rate', 0) if report else 0,
                'avg_return': report.performance_metrics.get('avg_return', 0) if report else 0,
                'recommendations_count': len(report.recommendations) if report and report.recommendations else 0
            } if status == 'SUCCESS' else {},
            'error_message': error_message if error_message else None
        }
        
        # In a real system, this would send to a message queue or callback endpoint
        # For now, save to a confirmation file
        try:
            confirmation_file = self.data_dir / f"confirmation_{request_id}.json"
            with open(confirmation_file, 'w') as f:
                json.dump(confirmation, f, indent=2)
            logger.info(f"Confirmation sent to Orchestration Agent: {confirmation_file}")
            
        except Exception as e:
            logger.error(f"Failed to send confirmation: {e}")


# ============ DEMONSTRATION AND TESTING ============

if __name__ == "__main__":
    # Initialize the enhanced backtesting agent
    agent = EnhancedBacktestingAgent()
    
    # Example 1: Start the agent in listening mode
    print("Starting Enhanced Backtesting Agent...")
    agent.start_listening()
    
    # Example 2: Send a VALIDATE_ALGORITHMS command
    test_command = Command(
        type=CommandType.VALIDATE_ALGORITHMS,
        payload={
            'strategies': ['hybrid_v1'],
            'holding_periods': [5, 10],
            'max_candidates': 20
        },
        timestamp=datetime.now(),
        request_id="test_validation_001"
    )
    
    agent.send_command(test_command)
    
    # Wait for processing
    time.sleep(2)
    
    # Example 3: Check status
    status_command = Command(
        type=CommandType.STATUS_CHECK,
        payload={},
        timestamp=datetime.now(),
        request_id="status_check_001"
    )
    
    agent.send_command(status_command)
    
    # Wait and then shutdown
    time.sleep(5)
    agent.stop_listening()
    
    print("Enhanced Backtesting Agent demonstration completed.")
    print("Check the validation_reports directory for generated reports.")
    
    # Also run basic legacy functionality for compatibility
    legacy_agent = BacktestingAgent()
    success = legacy_agent.execute(holding_days=5, max_symbols=10)
    
    if success:
        print("Legacy backtesting completed successfully.")
    else:
        print("Legacy backtesting failed.")