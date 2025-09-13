"""
Comprehensive Error Handler and Validator

Provides centralized error handling, logging, and validation for the API Integration Agent.
Handles edge cases, validation errors, and provides structured error responses.
"""

import json
import logging
import traceback
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Union, Tuple
from dataclasses import dataclass, asdict
from enum import Enum

from fastapi import HTTPException
from pydantic import BaseModel, ValidationError


class ErrorSeverity(Enum):
    """Error severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """Error categories for classification."""
    VALIDATION = "validation"
    REDIS = "redis"
    NETWORK = "network"
    DISCOVERY = "discovery"
    AUTHENTICATION = "authentication"
    RATE_LIMIT = "rate_limit"
    SYSTEM = "system"
    UNKNOWN = "unknown"


@dataclass
class ErrorContext:
    """Error context information."""
    request_id: str
    endpoint: str
    user_id: Optional[str] = None
    strategy: Optional[str] = None
    limit: Optional[int] = None
    timestamp: Optional[str] = None
    additional_data: Optional[Dict[str, Any]] = None


@dataclass
class StructuredError:
    """Structured error representation."""
    error_id: str
    category: ErrorCategory
    severity: ErrorSeverity
    message: str
    details: Optional[str] = None
    context: Optional[ErrorContext] = None
    stack_trace: Optional[str] = None
    suggestions: Optional[List[str]] = None
    timestamp: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            k: v.value if isinstance(v, Enum) else (asdict(v) if hasattr(v, '__dict__') else v)
            for k, v in asdict(self).items() if v is not None
        }


class APIErrorHandler:
    """
    Comprehensive error handler for API Integration Agent.
    
    Features:
    - Structured error logging
    - Error categorization and severity assessment
    - Edge case detection and handling
    - Error recovery suggestions
    - Performance impact tracking
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Error tracking
        self.error_count = 0
        self.error_history = []
        self.error_patterns = {}
        
        # Rate limiting tracking
        self.rate_limit_errors = 0
        self.last_rate_limit = None
        
        # Performance impact tracking
        self.performance_degradation_events = []
    
    def handle_error(
        self,
        exception: Exception,
        context: ErrorContext,
        include_stack_trace: bool = True
    ) -> StructuredError:
        """
        Handle and categorize an error with comprehensive logging.
        
        Args:
            exception: The exception that occurred
            context: Error context information
            include_stack_trace: Whether to include stack trace
            
        Returns:
            StructuredError: Structured error representation
        """
        try:
            # Generate unique error ID
            error_id = f"err_{int(time.time() * 1000)}_{hash(str(exception)) % 10000:04d}"
            
            # Categorize the error
            category = self._categorize_error(exception)
            severity = self._assess_severity(exception, category)
            
            # Extract error details
            message = str(exception)
            details = self._extract_error_details(exception)
            stack_trace = traceback.format_exc() if include_stack_trace else None
            suggestions = self._generate_suggestions(exception, category)
            
            # Create structured error
            structured_error = StructuredError(
                error_id=error_id,
                category=category,
                severity=severity,
                message=message,
                details=details,
                context=context,
                stack_trace=stack_trace,
                suggestions=suggestions,
                timestamp=datetime.utcnow().isoformat()
            )
            
            # Log the error
            self._log_structured_error(structured_error)
            
            # Track error patterns
            self._track_error_pattern(structured_error)
            
            # Update performance impact if needed
            if severity in [ErrorSeverity.HIGH, ErrorSeverity.CRITICAL]:
                self._track_performance_impact(structured_error)
            
            self.error_count += 1
            
            return structured_error
            
        except Exception as handling_error:
            # Fallback error handling
            self.logger.critical(f"Error handler failed: {str(handling_error)}", exc_info=True)
            
            return StructuredError(
                error_id="err_handler_failure",
                category=ErrorCategory.SYSTEM,
                severity=ErrorSeverity.CRITICAL,
                message=f"Error handling failed: {str(handling_error)}",
                context=context,
                timestamp=datetime.utcnow().isoformat()
            )
    
    def validate_discovery_response(
        self,
        response_data: Dict[str, Any],
        endpoint: str
    ) -> Tuple[bool, List[str]]:
        """
        Validate discovery API response format and content.
        
        Args:
            response_data: Response data to validate
            endpoint: Endpoint that generated the response
            
        Returns:
            Tuple of (is_valid, validation_errors)
        """
        validation_errors = []
        
        try:
            # Basic structure validation
            if not isinstance(response_data, dict):
                validation_errors.append("Response must be a dictionary")
                return False, validation_errors
            
            # Endpoint-specific validation
            if endpoint in ['/discovery/contenders', '/discovery/enhanced/contenders']:
                validation_errors.extend(self._validate_contenders_response(response_data))
            
            elif endpoint in ['/discovery/squeeze-candidates', '/discovery/enhanced/squeeze-candidates']:
                validation_errors.extend(self._validate_squeeze_response(response_data))
            
            elif endpoint in ['/discovery/health', '/discovery/enhanced/health']:
                validation_errors.extend(self._validate_health_response(response_data))
            
            # Common validations
            validation_errors.extend(self._validate_common_fields(response_data))
            
            return len(validation_errors) == 0, validation_errors
            
        except Exception as e:
            validation_errors.append(f"Validation failed: {str(e)}")
            return False, validation_errors
    
    def validate_request_parameters(
        self,
        params: Dict[str, Any],
        endpoint: str
    ) -> Tuple[bool, List[str]]:
        """
        Validate request parameters for discovery endpoints.
        
        Args:
            params: Request parameters to validate
            endpoint: Target endpoint
            
        Returns:
            Tuple of (is_valid, validation_errors)
        """
        validation_errors = []
        
        try:
            # Common parameter validations
            if 'limit' in params:
                limit = params['limit']
                if not isinstance(limit, int) or limit <= 0 or limit > 1000:
                    validation_errors.append("'limit' must be an integer between 1 and 1000")
            
            if 'strategy' in params:
                strategy = params['strategy']
                valid_strategies = ['legacy_v0', 'hybrid_v1', '']
                if strategy and strategy not in valid_strategies:
                    validation_errors.append(f"'strategy' must be one of: {valid_strategies}")
            
            # Endpoint-specific validations
            if 'squeeze-candidates' in endpoint:
                if 'min_score' in params:
                    min_score = params['min_score']
                    if not isinstance(min_score, (int, float)) or min_score < 0 or min_score > 1:
                        validation_errors.append("'min_score' must be a number between 0 and 1")
            
            return len(validation_errors) == 0, validation_errors
            
        except Exception as e:
            validation_errors.append(f"Parameter validation failed: {str(e)}")
            return False, validation_errors
    
    def handle_edge_cases(
        self,
        scenario: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Handle known edge cases with appropriate responses.
        
        Args:
            scenario: Edge case scenario identifier
            context: Context information
            
        Returns:
            Appropriate response for the edge case
        """
        try:
            if scenario == "empty_redis_cache":
                return {
                    'candidates': [],
                    'count': 0,
                    'status': 'ready',
                    'message': 'No cached discovery results available. Trigger discovery to populate cache.',
                    'edge_case': scenario,
                    'timestamp': datetime.utcnow().isoformat()
                }
            
            elif scenario == "redis_connection_failed":
                return {
                    'error': 'Redis connection unavailable',
                    'message': 'Discovery data temporarily unavailable. Please try again in a moment.',
                    'fallback_available': True,
                    'edge_case': scenario,
                    'timestamp': datetime.utcnow().isoformat()
                }
            
            elif scenario == "discovery_job_timeout":
                return {
                    'status': 'timeout',
                    'message': 'Discovery analysis taking longer than expected. Check /discovery/status for progress.',
                    'estimated_completion': '2-5 minutes',
                    'edge_case': scenario,
                    'timestamp': datetime.utcnow().isoformat()
                }
            
            elif scenario == "corrupted_cache_data":
                return {
                    'candidates': [],
                    'count': 0,
                    'status': 'error',
                    'message': 'Cached data corrupted. Fresh discovery analysis required.',
                    'recovery_action': 'trigger_discovery',
                    'edge_case': scenario,
                    'timestamp': datetime.utcnow().isoformat()
                }
            
            elif scenario == "rate_limit_exceeded":
                return {
                    'error': 'Rate limit exceeded',
                    'message': 'Too many requests. Please wait before retrying.',
                    'retry_after': 60,
                    'edge_case': scenario,
                    'timestamp': datetime.utcnow().isoformat()
                }
            
            else:
                return {
                    'error': 'Unknown edge case',
                    'message': f'Unhandled edge case: {scenario}',
                    'context': context,
                    'edge_case': scenario,
                    'timestamp': datetime.utcnow().isoformat()
                }
                
        except Exception as e:
            self.logger.error(f"Edge case handling failed: {str(e)}", exc_info=True)
            return {
                'error': 'Edge case handling failed',
                'message': 'Internal error during edge case processing',
                'details': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }
    
    def get_error_statistics(self) -> Dict[str, Any]:
        """Get error tracking statistics."""
        try:
            # Calculate error rates by category
            category_counts = {}
            severity_counts = {}
            
            for error in self.error_history[-100:]:  # Last 100 errors
                category = error.get('category', 'unknown')
                severity = error.get('severity', 'unknown')
                
                category_counts[category] = category_counts.get(category, 0) + 1
                severity_counts[severity] = severity_counts.get(severity, 0) + 1
            
            return {
                'total_errors': self.error_count,
                'recent_errors': len(self.error_history[-100:]),
                'category_distribution': category_counts,
                'severity_distribution': severity_counts,
                'error_patterns': len(self.error_patterns),
                'rate_limit_errors': self.rate_limit_errors,
                'performance_degradation_events': len(self.performance_degradation_events),
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error statistics calculation failed: {str(e)}")
            return {
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }
    
    # Private helper methods
    
    def _categorize_error(self, exception: Exception) -> ErrorCategory:
        """Categorize error based on exception type and message."""
        exception_name = type(exception).__name__
        message = str(exception).lower()
        
        if isinstance(exception, ValidationError):
            return ErrorCategory.VALIDATION
        elif isinstance(exception, HTTPException):
            if exception.status_code == 429:
                return ErrorCategory.RATE_LIMIT
            elif exception.status_code in [401, 403]:
                return ErrorCategory.AUTHENTICATION
            else:
                return ErrorCategory.NETWORK
        elif 'redis' in message or 'connection' in message:
            return ErrorCategory.REDIS
        elif 'discovery' in message or 'squeeze' in message:
            return ErrorCategory.DISCOVERY
        elif 'timeout' in message or 'network' in message:
            return ErrorCategory.NETWORK
        else:
            return ErrorCategory.UNKNOWN
    
    def _assess_severity(self, exception: Exception, category: ErrorCategory) -> ErrorSeverity:
        """Assess error severity based on type and impact."""
        if category == ErrorCategory.CRITICAL:
            return ErrorSeverity.CRITICAL
        elif category == ErrorCategory.REDIS and 'connection' in str(exception).lower():
            return ErrorSeverity.HIGH
        elif category == ErrorCategory.RATE_LIMIT:
            return ErrorSeverity.MEDIUM
        elif category == ErrorCategory.VALIDATION:
            return ErrorSeverity.LOW
        elif isinstance(exception, HTTPException) and exception.status_code >= 500:
            return ErrorSeverity.HIGH
        else:
            return ErrorSeverity.MEDIUM
    
    def _extract_error_details(self, exception: Exception) -> str:
        """Extract detailed error information."""
        details = []
        
        if hasattr(exception, 'detail'):
            details.append(f"Detail: {exception.detail}")
        
        if hasattr(exception, 'status_code'):
            details.append(f"Status Code: {exception.status_code}")
        
        if hasattr(exception, 'errors'):
            details.append(f"Validation Errors: {exception.errors()}")
        
        return "; ".join(details) if details else None
    
    def _generate_suggestions(self, exception: Exception, category: ErrorCategory) -> List[str]:
        """Generate recovery suggestions based on error type."""
        suggestions = []
        
        if category == ErrorCategory.REDIS:
            suggestions.extend([
                "Check Redis connection status",
                "Verify Redis service is running",
                "Check network connectivity to Redis server"
            ])
        elif category == ErrorCategory.VALIDATION:
            suggestions.extend([
                "Verify request parameters are correct",
                "Check API documentation for required fields",
                "Ensure data types match expected format"
            ])
        elif category == ErrorCategory.RATE_LIMIT:
            suggestions.extend([
                "Reduce request frequency",
                "Implement exponential backoff",
                "Check rate limit headers"
            ])
        elif category == ErrorCategory.DISCOVERY:
            suggestions.extend([
                "Check if discovery system is operational",
                "Verify market data feeds are available",
                "Try triggering fresh discovery analysis"
            ])
        
        return suggestions
    
    def _log_structured_error(self, error: StructuredError):
        """Log structured error with appropriate level."""
        extra_data = {
            'error_id': error.error_id,
            'category': error.category.value,
            'severity': error.severity.value
        }
        
        if error.context:
            extra_data.update({
                'request_id': error.context.request_id,
                'endpoint': error.context.endpoint,
                'strategy': error.context.strategy
            })
        
        if error.severity == ErrorSeverity.CRITICAL:
            self.logger.critical(error.message, extra=extra_data)
        elif error.severity == ErrorSeverity.HIGH:
            self.logger.error(error.message, extra=extra_data)
        elif error.severity == ErrorSeverity.MEDIUM:
            self.logger.warning(error.message, extra=extra_data)
        else:
            self.logger.info(error.message, extra=extra_data)
    
    def _track_error_pattern(self, error: StructuredError):
        """Track error patterns for analysis."""
        pattern_key = f"{error.category.value}:{error.message[:50]}"
        
        if pattern_key not in self.error_patterns:
            self.error_patterns[pattern_key] = {
                'count': 0,
                'first_seen': error.timestamp,
                'last_seen': error.timestamp,
                'severity': error.severity.value
            }
        
        self.error_patterns[pattern_key]['count'] += 1
        self.error_patterns[pattern_key]['last_seen'] = error.timestamp
        
        # Keep error history limited
        self.error_history.append(error.to_dict())
        if len(self.error_history) > 1000:
            self.error_history = self.error_history[-500:]  # Keep last 500
    
    def _track_performance_impact(self, error: StructuredError):
        """Track performance degradation events."""
        self.performance_degradation_events.append({
            'error_id': error.error_id,
            'category': error.category.value,
            'severity': error.severity.value,
            'timestamp': error.timestamp
        })
        
        # Keep list limited
        if len(self.performance_degradation_events) > 100:
            self.performance_degradation_events = self.performance_degradation_events[-50:]
    
    def _validate_contenders_response(self, data: Dict[str, Any]) -> List[str]:
        """Validate contenders response format."""
        errors = []
        
        if 'candidates' not in data:
            errors.append("Missing 'candidates' field")
        elif not isinstance(data['candidates'], list):
            errors.append("'candidates' must be a list")
        else:
            for i, candidate in enumerate(data['candidates']):
                if not isinstance(candidate, dict):
                    errors.append(f"Candidate {i} must be a dictionary")
                elif 'symbol' not in candidate:
                    errors.append(f"Candidate {i} missing 'symbol' field")
        
        if 'count' not in data:
            errors.append("Missing 'count' field")
        elif not isinstance(data['count'], int):
            errors.append("'count' must be an integer")
        
        return errors
    
    def _validate_squeeze_response(self, data: Dict[str, Any]) -> List[str]:
        """Validate squeeze candidates response format."""
        errors = self._validate_contenders_response(data)  # Base validation
        
        if 'min_score_threshold' not in data:
            errors.append("Missing 'min_score_threshold' field")
        
        return errors
    
    def _validate_health_response(self, data: Dict[str, Any]) -> List[str]:
        """Validate health response format."""
        errors = []
        
        if 'status' not in data:
            errors.append("Missing 'status' field")
        
        if 'timestamp' not in data:
            errors.append("Missing 'timestamp' field")
        
        return errors
    
    def _validate_common_fields(self, data: Dict[str, Any]) -> List[str]:
        """Validate common response fields."""
        errors = []
        
        # Check for required timestamp
        if 'timestamp' in data:
            try:
                datetime.fromisoformat(data['timestamp'].replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                errors.append("'timestamp' must be a valid ISO format datetime")
        
        return errors


# Global error handler instance
_error_handler = None

def get_error_handler() -> APIErrorHandler:
    """Get singleton error handler instance."""
    global _error_handler
    if _error_handler is None:
        _error_handler = APIErrorHandler()
    return _error_handler