"""
API Response Format Validator

Comprehensive validation system for API responses to ensure consistent format,
data integrity, and frontend compatibility across all discovery endpoints.
"""

import json
import logging
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Union, Tuple
from dataclasses import dataclass
from enum import Enum

from pydantic import BaseModel, Field, validator, ValidationError


class ResponseFormat(Enum):
    """Expected response format types."""
    CONTENDERS = "contenders"
    SQUEEZE_CANDIDATES = "squeeze_candidates"
    HEALTH = "health"
    TRIGGER = "trigger"
    METRICS = "metrics"
    ERROR = "error"


@dataclass
class ValidationRule:
    """Validation rule definition."""
    field_name: str
    required: bool
    expected_type: type
    constraints: Optional[Dict[str, Any]] = None
    description: Optional[str] = None


class ContendersResponse(BaseModel):
    """Pydantic model for contenders response validation."""
    candidates: List[Dict[str, Any]] = Field(..., description="List of discovery candidates")
    count: int = Field(..., ge=0, description="Number of candidates returned")
    strategy: str = Field("", description="Strategy used for discovery")
    timestamp: str = Field(..., description="Response timestamp")
    meta: Optional[Dict[str, Any]] = Field(None, description="Response metadata")
    
    @validator('candidates')
    def validate_candidates(cls, v):
        """Validate candidates structure."""
        if not isinstance(v, list):
            raise ValueError("candidates must be a list")
        
        for i, candidate in enumerate(v):
            if not isinstance(candidate, dict):
                raise ValueError(f"Candidate {i} must be a dictionary")
            
            required_fields = ['symbol']
            for field in required_fields:
                if field not in candidate:
                    raise ValueError(f"Candidate {i} missing required field: {field}")
            
            # Validate symbol format
            symbol = candidate.get('symbol', '')
            if not isinstance(symbol, str) or len(symbol) == 0:
                raise ValueError(f"Candidate {i} symbol must be a non-empty string")
        
        return v
    
    @validator('timestamp')
    def validate_timestamp(cls, v):
        """Validate timestamp format."""
        try:
            datetime.fromisoformat(v.replace('Z', '+00:00'))
        except ValueError:
            raise ValueError("timestamp must be a valid ISO format datetime")
        return v


class SqueezeCandidatesResponse(BaseModel):
    """Pydantic model for squeeze candidates response validation."""
    candidates: List[Dict[str, Any]] = Field(..., description="List of squeeze candidates")
    count: int = Field(..., ge=0, description="Number of candidates returned")
    min_score_threshold: float = Field(..., ge=0.0, le=1.0, description="Minimum score threshold")
    strategy: str = Field("", description="Strategy used")
    timestamp: str = Field(..., description="Response timestamp")
    
    @validator('candidates')
    def validate_squeeze_candidates(cls, v):
        """Validate squeeze candidates structure."""
        if not isinstance(v, list):
            raise ValueError("candidates must be a list")
        
        for i, candidate in enumerate(v):
            if not isinstance(candidate, dict):
                raise ValueError(f"Candidate {i} must be a dictionary")
            
            # Required fields for squeeze candidates
            required_fields = ['symbol', 'squeeze_score']
            for field in required_fields:
                if field not in candidate:
                    raise ValueError(f"Squeeze candidate {i} missing required field: {field}")
            
            # Validate squeeze_score range
            squeeze_score = candidate.get('squeeze_score')
            if not isinstance(squeeze_score, (int, float)) or squeeze_score < 0 or squeeze_score > 1:
                raise ValueError(f"Squeeze candidate {i} squeeze_score must be between 0 and 1")
        
        return v


class HealthResponse(BaseModel):
    """Pydantic model for health response validation."""
    status: str = Field(..., description="Health status")
    timestamp: str = Field(..., description="Health check timestamp")
    
    @validator('status')
    def validate_status(cls, v):
        """Validate status values."""
        valid_statuses = ['healthy', 'degraded', 'unhealthy', 'error']
        if v not in valid_statuses:
            raise ValueError(f"status must be one of: {valid_statuses}")
        return v


class APIResponseValidator:
    """
    Comprehensive API response validator for discovery endpoints.
    
    Features:
    - Format validation using Pydantic models
    - Data integrity checks
    - Frontend compatibility validation
    - Performance impact assessment
    - Custom validation rules
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Validation statistics
        self.validations_performed = 0
        self.validation_failures = 0
        self.validation_warnings = 0
        
        # Performance tracking
        self.validation_times = []
        
        # Custom validation rules
        self.custom_rules = {}
    
    def validate_response(
        self,
        response_data: Dict[str, Any],
        response_format: ResponseFormat,
        strict_mode: bool = True
    ) -> Tuple[bool, List[str], List[str]]:
        """
        Validate API response against expected format.
        
        Args:
            response_data: Response data to validate
            response_format: Expected response format
            strict_mode: Whether to use strict validation
            
        Returns:
            Tuple of (is_valid, validation_errors, validation_warnings)
        """
        start_time = time.time()
        validation_errors = []
        validation_warnings = []
        
        try:
            self.validations_performed += 1
            
            # Format-specific validation
            if response_format == ResponseFormat.CONTENDERS:
                is_valid, errors, warnings = self._validate_contenders_response(
                    response_data, strict_mode
                )
            elif response_format == ResponseFormat.SQUEEZE_CANDIDATES:
                is_valid, errors, warnings = self._validate_squeeze_response(
                    response_data, strict_mode
                )
            elif response_format == ResponseFormat.HEALTH:
                is_valid, errors, warnings = self._validate_health_response(
                    response_data, strict_mode
                )
            elif response_format == ResponseFormat.TRIGGER:
                is_valid, errors, warnings = self._validate_trigger_response(
                    response_data, strict_mode
                )
            elif response_format == ResponseFormat.METRICS:
                is_valid, errors, warnings = self._validate_metrics_response(
                    response_data, strict_mode
                )
            elif response_format == ResponseFormat.ERROR:
                is_valid, errors, warnings = self._validate_error_response(
                    response_data, strict_mode
                )
            else:
                is_valid = False
                errors = [f"Unknown response format: {response_format}"]
                warnings = []
            
            validation_errors.extend(errors)
            validation_warnings.extend(warnings)
            
            # Common validations
            common_errors, common_warnings = self._validate_common_fields(response_data)
            validation_errors.extend(common_errors)
            validation_warnings.extend(common_warnings)
            
            # Frontend compatibility checks
            compat_errors, compat_warnings = self._check_frontend_compatibility(response_data)
            validation_errors.extend(compat_errors)
            validation_warnings.extend(compat_warnings)
            
            # Performance impact assessment
            perf_warnings = self._assess_performance_impact(response_data)
            validation_warnings.extend(perf_warnings)
            
            # Update statistics
            if validation_errors:
                self.validation_failures += 1
            if validation_warnings:
                self.validation_warnings += 1
            
            # Track validation time
            validation_time = time.time() - start_time
            self.validation_times.append(validation_time)
            if len(self.validation_times) > 100:
                self.validation_times = self.validation_times[-50:]  # Keep last 50
            
            is_valid = len(validation_errors) == 0
            
            # Log validation results
            self._log_validation_result(
                response_format, is_valid, validation_errors, validation_warnings, validation_time
            )
            
            return is_valid, validation_errors, validation_warnings
            
        except Exception as e:
            self.logger.error(f"Response validation failed: {str(e)}", exc_info=True)
            return False, [f"Validation process failed: {str(e)}"], []
    
    def add_custom_rule(self, field_path: str, rule: ValidationRule):
        """
        Add custom validation rule.
        
        Args:
            field_path: Dot notation field path (e.g., "meta.processing_time_ms")
            rule: Validation rule to apply
        """
        self.custom_rules[field_path] = rule
    
    def get_validation_statistics(self) -> Dict[str, Any]:
        """Get validation performance statistics."""
        avg_validation_time = (
            sum(self.validation_times) / len(self.validation_times)
            if self.validation_times else 0
        )
        
        return {
            'validations_performed': self.validations_performed,
            'validation_failures': self.validation_failures,
            'validation_warnings': self.validation_warnings,
            'failure_rate': (
                self.validation_failures / max(self.validations_performed, 1)
            ) * 100,
            'warning_rate': (
                self.validation_warnings / max(self.validations_performed, 1)
            ) * 100,
            'avg_validation_time_ms': round(avg_validation_time * 1000, 2),
            'custom_rules_count': len(self.custom_rules),
            'timestamp': datetime.utcnow().isoformat()
        }
    
    def validate_data_integrity(
        self,
        response_data: Dict[str, Any]
    ) -> Tuple[bool, List[str]]:
        """
        Validate data integrity and consistency.
        
        Args:
            response_data: Response data to check
            
        Returns:
            Tuple of (is_consistent, integrity_issues)
        """
        integrity_issues = []
        
        try:
            # Check count consistency
            if 'candidates' in response_data and 'count' in response_data:
                actual_count = len(response_data['candidates'])
                declared_count = response_data['count']
                
                if actual_count != declared_count:
                    integrity_issues.append(
                        f"Count mismatch: declared {declared_count}, actual {actual_count}"
                    )
            
            # Check score ranges for candidates
            if 'candidates' in response_data:
                for i, candidate in enumerate(response_data['candidates']):
                    if 'score' in candidate:
                        score = candidate['score']
                        if isinstance(score, (int, float)):
                            if score < 0 or score > 100:
                                integrity_issues.append(
                                    f"Candidate {i} score {score} outside valid range (0-100)"
                                )
                    
                    if 'squeeze_score' in candidate:
                        squeeze_score = candidate['squeeze_score']
                        if isinstance(squeeze_score, (int, float)):
                            if squeeze_score < 0 or squeeze_score > 1:
                                integrity_issues.append(
                                    f"Candidate {i} squeeze_score {squeeze_score} outside valid range (0-1)"
                                )
            
            # Check timestamp consistency
            if 'timestamp' in response_data:
                try:
                    response_time = datetime.fromisoformat(
                        response_data['timestamp'].replace('Z', '+00:00')
                    )
                    now = datetime.now(timezone.utc)
                    
                    # Check if timestamp is reasonable (not too far in past/future)
                    time_diff = abs((now - response_time).total_seconds())
                    if time_diff > 3600:  # 1 hour
                        integrity_issues.append(
                            f"Timestamp appears stale or incorrect: {response_data['timestamp']}"
                        )
                        
                except ValueError:
                    integrity_issues.append(f"Invalid timestamp format: {response_data['timestamp']}")
            
            # Check for duplicate symbols
            if 'candidates' in response_data:
                symbols = []
                for candidate in response_data['candidates']:
                    symbol = candidate.get('symbol')
                    if symbol:
                        if symbol in symbols:
                            integrity_issues.append(f"Duplicate symbol found: {symbol}")
                        symbols.append(symbol)
            
            return len(integrity_issues) == 0, integrity_issues
            
        except Exception as e:
            self.logger.error(f"Data integrity check failed: {str(e)}")
            return False, [f"Integrity check failed: {str(e)}"]
    
    # Private validation methods
    
    def _validate_contenders_response(
        self, 
        data: Dict[str, Any], 
        strict_mode: bool
    ) -> Tuple[bool, List[str], List[str]]:
        """Validate contenders response format."""
        errors = []
        warnings = []
        
        try:
            # Use Pydantic model for validation
            ContendersResponse(**data)
            
        except ValidationError as e:
            for error in e.errors():
                field = ".".join(str(loc) for loc in error['loc'])
                message = error['msg']
                errors.append(f"Field '{field}': {message}")
        
        # Additional business logic validations
        if 'candidates' in data:
            candidates = data['candidates']
            
            # Check for empty results warning
            if len(candidates) == 0:
                warnings.append("No candidates returned - market conditions may not be favorable")
            
            # Check for high count without strategy
            if len(candidates) > 100 and not data.get('strategy'):
                warnings.append("High candidate count without explicit strategy may indicate loose filtering")
            
            # Validate candidate quality
            for i, candidate in enumerate(candidates):
                if 'score' in candidate:
                    score = candidate.get('score', 0)
                    if isinstance(score, (int, float)) and score < 10:
                        warnings.append(f"Candidate {i} ({candidate.get('symbol')}) has very low score: {score}")
        
        return len(errors) == 0, errors, warnings
    
    def _validate_squeeze_response(
        self, 
        data: Dict[str, Any], 
        strict_mode: bool
    ) -> Tuple[bool, List[str], List[str]]:
        """Validate squeeze candidates response format."""
        errors = []
        warnings = []
        
        try:
            # Use Pydantic model for validation
            SqueezeCandidatesResponse(**data)
            
        except ValidationError as e:
            for error in e.errors():
                field = ".".join(str(loc) for loc in error['loc'])
                message = error['msg']
                errors.append(f"Field '{field}': {message}")
        
        # Additional squeeze-specific validations
        if 'candidates' in data:
            candidates = data['candidates']
            min_threshold = data.get('min_score_threshold', 0)
            
            # Check if all candidates meet minimum threshold
            for i, candidate in enumerate(candidates):
                squeeze_score = candidate.get('squeeze_score', 0)
                if squeeze_score < min_threshold:
                    errors.append(
                        f"Candidate {i} squeeze_score {squeeze_score} below threshold {min_threshold}"
                    )
            
            # Warning for very low thresholds
            if min_threshold < 0.1:
                warnings.append("Very low minimum score threshold may return poor quality candidates")
        
        return len(errors) == 0, errors, warnings
    
    def _validate_health_response(
        self, 
        data: Dict[str, Any], 
        strict_mode: bool
    ) -> Tuple[bool, List[str], List[str]]:
        """Validate health response format."""
        errors = []
        warnings = []
        
        try:
            # Use Pydantic model for validation
            HealthResponse(**data)
            
        except ValidationError as e:
            for error in e.errors():
                field = ".".join(str(loc) for loc in error['loc'])
                message = error['msg']
                errors.append(f"Field '{field}': {message}")
        
        # Health-specific warnings
        status = data.get('status', '').lower()
        if status in ['degraded', 'unhealthy']:
            warnings.append(f"System status is {status} - performance may be impacted")
        
        return len(errors) == 0, errors, warnings
    
    def _validate_trigger_response(
        self, 
        data: Dict[str, Any], 
        strict_mode: bool
    ) -> Tuple[bool, List[str], List[str]]:
        """Validate trigger response format."""
        errors = []
        warnings = []
        
        required_fields = ['success', 'timestamp']
        for field in required_fields:
            if field not in data:
                errors.append(f"Missing required field: {field}")
        
        return len(errors) == 0, errors, warnings
    
    def _validate_metrics_response(
        self, 
        data: Dict[str, Any], 
        strict_mode: bool
    ) -> Tuple[bool, List[str], List[str]]:
        """Validate metrics response format."""
        errors = []
        warnings = []
        
        # Basic structure check
        if not isinstance(data, dict):
            errors.append("Metrics response must be a dictionary")
        
        return len(errors) == 0, errors, warnings
    
    def _validate_error_response(
        self, 
        data: Dict[str, Any], 
        strict_mode: bool
    ) -> Tuple[bool, List[str], List[str]]:
        """Validate error response format."""
        errors = []
        warnings = []
        
        required_fields = ['error', 'timestamp']
        for field in required_fields:
            if field not in data:
                errors.append(f"Missing required field: {field}")
        
        return len(errors) == 0, errors, warnings
    
    def _validate_common_fields(self, data: Dict[str, Any]) -> Tuple[List[str], List[str]]:
        """Validate fields common to all responses."""
        errors = []
        warnings = []
        
        # Check for response metadata
        if 'meta' in data:
            meta = data['meta']
            if not isinstance(meta, dict):
                errors.append("'meta' field must be a dictionary")
            else:
                # Check for useful metadata
                useful_fields = ['processing_time_ms', 'cache_hit', 'source']
                if not any(field in meta for field in useful_fields):
                    warnings.append("Response metadata lacks performance/debugging information")
        
        return errors, warnings
    
    def _check_frontend_compatibility(
        self, 
        data: Dict[str, Any]
    ) -> Tuple[List[str], List[str]]:
        """Check frontend compatibility issues."""
        errors = []
        warnings = []
        
        # Check for fields that frontend expects
        if 'candidates' in data:
            candidates = data['candidates']
            if candidates:
                first_candidate = candidates[0]
                
                # Frontend typically expects certain fields
                expected_fields = ['symbol', 'price', 'score']
                missing_fields = [
                    field for field in expected_fields 
                    if field not in first_candidate
                ]
                
                if missing_fields:
                    warnings.append(
                        f"Candidates missing frontend-expected fields: {missing_fields}"
                    )
        
        # Check for overly large responses
        response_size = len(json.dumps(data))
        if response_size > 1024 * 1024:  # 1MB
            warnings.append(f"Large response size ({response_size} bytes) may impact frontend performance")
        
        return errors, warnings
    
    def _assess_performance_impact(self, data: Dict[str, Any]) -> List[str]:
        """Assess potential performance impact."""
        warnings = []
        
        # Check processing time
        meta = data.get('meta', {})
        processing_time = meta.get('processing_time_ms', 0)
        
        if processing_time > 5000:  # 5 seconds
            warnings.append(f"High processing time: {processing_time}ms")
        elif processing_time > 2000:  # 2 seconds
            warnings.append(f"Moderate processing time: {processing_time}ms")
        
        # Check candidate count impact
        if 'candidates' in data:
            candidate_count = len(data['candidates'])
            if candidate_count > 500:
                warnings.append(f"High candidate count ({candidate_count}) may impact client performance")
        
        return warnings
    
    def _log_validation_result(
        self,
        response_format: ResponseFormat,
        is_valid: bool,
        errors: List[str],
        warnings: List[str],
        validation_time: float
    ):
        """Log validation results."""
        log_data = {
            'format': response_format.value,
            'valid': is_valid,
            'error_count': len(errors),
            'warning_count': len(warnings),
            'validation_time_ms': round(validation_time * 1000, 2)
        }
        
        if errors:
            self.logger.warning(f"Response validation failed: {errors}", extra=log_data)
        elif warnings:
            self.logger.info(f"Response validation warnings: {warnings}", extra=log_data)
        else:
            self.logger.debug("Response validation passed", extra=log_data)


# Global validator instance
_response_validator = None

def get_response_validator() -> APIResponseValidator:
    """Get singleton response validator instance."""
    global _response_validator
    if _response_validator is None:
        _response_validator = APIResponseValidator()
    return _response_validator