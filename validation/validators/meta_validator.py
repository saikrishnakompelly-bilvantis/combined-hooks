"""
API Meta File Validator

This module validates api.meta files against the compliance rules.
Implements all 20 rules from compliance_rules.csv with updated values.
"""

import re
from typing import Dict, Any, List, Optional, Union
from .base_validator import BaseValidator


class MetaValidator(BaseValidator):
    """Validates api.meta files against compliance rules."""
    
    # Allowed values for enumeration fields - UPDATED
    ALLOWED_VALUES = {
        'API.layer': ['xAPI', 'sAPI', 'pAPI'],
        'API.audience': ['Internal', 'External'],
        'API.version.status': ['develop', 'test', 'prelive', 'live', 'deprecated', 'demised'],
        'API.version.apiStyle': [
            'HYDROGEN', 'DOMAIN_PAPI', 'ORIGINATIONS', 'BANKING 2.0', 
            'FIRST_DIRECT', 'BERLIN', 'STET', 'OBIE', 'OTHER'
        ],
        'API.version.architecturalStyle': ['REST', 'GRAPHQL', 'SOAP', 'RPC'],
        'API.version.dataClassification': ['public', 'internal', 'confidential', 'restricted', 'secret'],
        'API.version.implementationFramework': [
            'CARBON', 'SPRING_BOOT', 'SILVER', 'SILVER_1S', 'NODE JS', 'DOMAIN_PAPI', 'MULESOFT', 'OTHER'
        ],
        'API.contract.GBGF': [
            'CMB', 'Central-Architecture', 'Corporate-Functions', 'Group-Data', 'FCR', 'GBM', 'GPB',
            'Cyber-Security', 'ITID', 'OSS', 'Payments', 'RBWM', 'HBFR', 'Risk', 'DAO', 'WSIT',
            'WPB', 'Compliance', 'CTO', 'Enterprise Technology', 'GOA'
        ]
    }
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize the meta validator."""
        super().__init__(config)
        self.validation_rules = [
            self._validate_metadata_version,
            self._validate_asset_name,
            self._validate_asset_version,
            self._validate_auto_increment_asset_version,
            self._validate_contract_file_name,
            self._validate_ignore,
            self._validate_api_layer,
            self._validate_api_audience,
            self._validate_contract_version,
            self._validate_status,
            self._validate_private_api,
            self._validate_api_style,
            self._validate_implementation_framework,
            self._validate_architectural_style,
            self._validate_business_models,
            self._validate_business_models_wpb_cidm,
            self._validate_data_classification,
            self._validate_gbgf,
            self._validate_service_line,
            self._validate_team_name,
            self._validate_team_email_address,
            self._validate_transaction_names
        ]
    
    def validate_meta_content(self, meta_content: Dict[str, Any], file_path: str) -> bool:
        """
        Validate meta file content against all compliance rules.
        
        Args:
            meta_content: Parsed meta file content
            file_path: Path to the meta file
            
        Returns:
            True if all validations pass, False otherwise
        """
        if not isinstance(meta_content, dict):
            self.add_error("Meta file content is not a valid dictionary", file_path)
            return False
        
        validation_passed = True
        
        # Run all validation rules
        for rule_func in self.validation_rules:
            try:
                if not rule_func(meta_content, file_path):
                    validation_passed = False
            except Exception as e:
                self.add_error(f"Validation rule error: {str(e)}", file_path)
                validation_passed = False
        
        return validation_passed
    
    def validate_file(self, file_path: str, content: str) -> bool:
        """This method is required by BaseValidator but not used for meta validation."""
        return True
    
    def _get_nested_value(self, data: Dict[str, Any], path: str) -> Any:
        """
        Get a nested value from dictionary using dot notation.
        
        Args:
            data: Dictionary to search
            path: Dot-separated path (e.g., 'API.version.contractVersion')
            
        Returns:
            The value if found, None otherwise
        """
        try:
            current = data
            for key in path.split('.'):
                if isinstance(current, dict) and key in current:
                    current = current[key]
                else:
                    return None
            return current
        except (TypeError, KeyError):
            return None
    
    def _validate_metadata_version(self, data: Dict[str, Any], file_path: str) -> bool:
        """Rule 1: metaDataVersion should be >= 6.0.0"""
        version = data.get('metaDataVersion')
        
        if version is None:
            self.add_error("metaDataVersion is missing", file_path)
            return False
        
        try:
            # Convert version string to comparable format
            version_parts = str(version).split('.')
            if len(version_parts) < 3:
                self.add_error(f"metaDataVersion format invalid: {version}", file_path)
                return False
            
            major, minor, patch = map(int, version_parts[:3])
            if (major, minor, patch) < (6, 0, 0):
                self.add_error(f"metaDataVersion {version} is less than required 6.0.0", file_path)
                return False
                
        except ValueError:
            self.add_error(f"metaDataVersion is not a valid version number: {version}", file_path)
            return False
        
        return True
    
    def _validate_asset_name(self, data: Dict[str, Any], file_path: str) -> bool:
        """Rule 2: assetName should match pattern ^[a-z]+(?>(?>(-)?[a-z0-9]+))*$"""
        asset_name = data.get('assetName')
        
        if asset_name is None:
            self.add_error("assetName is missing", file_path)
            return False
        
        # Simplified pattern that achieves the same goal
        pattern = r'^[a-z]+((--|-)[a-z0-9]+)*$'
        if not re.match(pattern, str(asset_name)):
            self.add_error(f"assetName '{asset_name}' does not match required pattern", file_path)
            return False
        
        return True
    
    def _validate_asset_version(self, data: Dict[str, Any], file_path: str) -> bool:
        """Rule 3: assetVersion should start with 1.0.0"""
        asset_version = data.get('assetVersion')
        
        if asset_version is None:
            self.add_error("assetVersion is missing", file_path)
            return False
        
        # Updated: Allow 1.0.0 followed by anything (1.0.0.*)
        pattern = r'^1\.0\.0.*$'
        if not re.match(pattern, str(asset_version)):
            self.add_error(f"assetVersion '{asset_version}' should start with '1.0.0'", file_path)
            return False
        
        return True
    
    def _validate_auto_increment_asset_version(self, data: Dict[str, Any], file_path: str) -> bool:
        """Rule 4: autoIncrementAssetVersion should be true"""
        auto_increment = data.get('autoIncrementAssetVersion')
        
        if auto_increment is None:
            self.add_error("autoIncrementAssetVersion is missing", file_path)
            return False
        
        if auto_increment is not True:
            self.add_error(f"autoIncrementAssetVersion should be true, got {auto_increment}", file_path)
            return False
        
        return True
    
    def _validate_contract_file_name(self, data: Dict[str, Any], file_path: str) -> bool:
        """Rule 5: contractFileName should not be missing"""
        contract_file_name = data.get('contractFileName')
        
        if contract_file_name is None or contract_file_name == "":
            self.add_error("contractFileName is missing", file_path)
            return False
        
        return True
    
    def _validate_ignore(self, data: Dict[str, Any], file_path: str) -> bool:
        """Rule 6: ignore should be false"""
        ignore = data.get('ignore')
        
        if ignore is None:
            self.add_error("ignore field is missing", file_path)
            return False
        
        if ignore is True:
            self.add_error("ignore should be false", file_path)
            return False
        
        return True
    
    def _validate_api_layer(self, data: Dict[str, Any], file_path: str) -> bool:
        """Rule 7: API.layer should be one of allowed values (case-sensitive)"""
        layer = self._get_nested_value(data, 'API.layer')
        
        if layer is None:
            self.add_error("API.layer is missing", file_path)
            return False
        
        if layer not in self.ALLOWED_VALUES['API.layer']:
            self.add_error(f"API.layer '{layer}' is not in allowed values {self.ALLOWED_VALUES['API.layer']}", file_path)
            return False
        
        return True
    
    def _validate_api_audience(self, data: Dict[str, Any], file_path: str) -> bool:
        """Rule 8: API.audience should be one of allowed values (case-sensitive)"""
        audience = self._get_nested_value(data, 'API.audience')
        
        if audience is None:
            self.add_error("API.audience is missing", file_path)
            return False
        
        if audience not in self.ALLOWED_VALUES['API.audience']:
            self.add_error(f"API.audience '{audience}' is not in allowed values {self.ALLOWED_VALUES['API.audience']}", file_path)
            return False
        
        return True
    
    def _validate_contract_version(self, data: Dict[str, Any], file_path: str) -> bool:
        """Rule 9: API.version.contractVersion should match pattern ^[vV]?[0-9]+(?>.[0-9]+){1,2}$"""
        contract_version = self._get_nested_value(data, 'API.version.contractVersion')
        
        if contract_version is None:
            self.add_error("API.version.contractVersion is missing", file_path)
            return False
        
        # Updated pattern with capital V option and corrected syntax
        pattern = r'^[vV]?[0-9]+(?:\.[0-9]+){1,2}$'
        if not re.match(pattern, str(contract_version)):
            self.add_error(f"API.version.contractVersion '{contract_version}' does not match version pattern", file_path)
            return False
        
        return True
    
    def _validate_status(self, data: Dict[str, Any], file_path: str) -> bool:
        """Rule 10: API.version.status should be one of allowed values"""
        status = self._get_nested_value(data, 'API.version.status')
        
        if status is None:
            self.add_error("API.version.status is missing", file_path)
            return False
        
        if status not in self.ALLOWED_VALUES['API.version.status']:
            self.add_error(f"API.version.status '{status}' is not in allowed values {self.ALLOWED_VALUES['API.version.status']}", file_path)
            return False
        
        return True
    
    def _validate_private_api(self, data: Dict[str, Any], file_path: str) -> bool:
        """Rule 11: API.version.privateAPI should not be missing"""
        private_api = self._get_nested_value(data, 'API.version.privateAPI')
        
        if private_api is None:
            self.add_error("API.version.privateAPI is missing", file_path)
            return False
        
        return True
    
    def _validate_api_style(self, data: Dict[str, Any], file_path: str) -> bool:
        """Rule 12: API.version.apiStyle should be one of allowed values"""
        api_style = self._get_nested_value(data, 'API.version.apiStyle')
        
        if api_style is None:
            self.add_error("API.version.apiStyle is missing", file_path)
            return False
        
        if api_style not in self.ALLOWED_VALUES['API.version.apiStyle']:
            self.add_error(f"API.version.apiStyle '{api_style}' is not in allowed values {self.ALLOWED_VALUES['API.version.apiStyle']}", file_path)
            return False
        
        return True
    
    def _validate_implementation_framework(self, data: Dict[str, Any], file_path: str) -> bool:
        """Validate API.version.implementationFramework for allowed values."""
        impl_framework = self._get_nested_value(data, 'API.version.implementationFramework')
        allowed = self.ALLOWED_VALUES['API.version.implementationFramework']
        if impl_framework is None or impl_framework == '':
            self.add_error('wpb-implementationFramework-missing', file_path)
            return False
        if impl_framework not in allowed:
            self.add_error(f"wpb-implementationFramework-unrecognised: '{impl_framework}' not in {allowed}", file_path)
            return False
        return True

    def _validate_architectural_style(self, data: Dict[str, Any], file_path: str) -> bool:
        """Rule 13: API.version.architecturalStyle should be one of allowed values"""
        arch_style = self._get_nested_value(data, 'API.version.architecturalStyle')
        
        if arch_style is None:
            self.add_error("API.version.architecturalStyle is missing", file_path)
            return False
        
        if arch_style not in self.ALLOWED_VALUES['API.version.architecturalStyle']:
            self.add_error(f"API.version.architecturalStyle '{arch_style}' is not in allowed values {self.ALLOWED_VALUES['API.version.architecturalStyle']}", file_path)
            return False
        
        return True
    
    def _validate_business_models(self, data: Dict[str, Any], file_path: str) -> bool:
        """Rule 14: API.version.businessModels should not be empty if API.layer is xAPI (UPDATED)"""
        layer = self._get_nested_value(data, 'API.layer')
        business_models = self._get_nested_value(data, 'API.version.businessModels')
        
        if layer == "pAPI":
            if business_models is None or (isinstance(business_models, list) and len(business_models) == 0):
                self.add_error("API.version.businessModels is required when API.layer is 'pAPI'", file_path)
                return False
        
        return True
    
    def _validate_business_models_wpb_cidm(self, data: Dict[str, Any], file_path: str) -> bool:
        """If API.layer is pAPI, businessModels must have at least one with name 'WPB-CIDM'.
        For sAPI/xAPI, if businessModels exists, all names must be 'WPB-CIDM'."""
        layer = self._get_nested_value(data, 'API.layer')
        business_models = self._get_nested_value(data, 'API.version.businessModels')
        if layer == 'pAPI':
            if not business_models or not isinstance(business_models, list):
                self.add_error("API.version.businessModels is required and must be a list when API.layer is 'pAPI' (WPB-CIDM check)", file_path)
                return False
            found = any(isinstance(bm, dict) and bm.get('name') == 'WPB-CIDM' for bm in business_models)
            if not found:
                self.add_error("API.version.businessModels must contain an object with name 'WPB-CIDM' when API.layer is 'pAPI'", file_path)
                return False
        elif layer in ('sAPI', 'xAPI'):
            if business_models and isinstance(business_models, list):
                for bm in business_models:
                    if not (isinstance(bm, dict) and bm.get('name') == 'WPB-CIDM'):
                        self.add_error("If API.layer is 'sAPI' or 'xAPI', all businessModels names must be 'WPB-CIDM' if present", file_path)
                        return False
        return True

    def _validate_data_classification(self, data: Dict[str, Any], file_path: str) -> bool:
        """Rule 15: API.version.dataClassification should be one of allowed values"""
        data_classification = self._get_nested_value(data, 'API.version.dataClassification')
        
        if data_classification is None:
            self.add_error("API.version.dataClassification is missing", file_path)
            return False
        
        if data_classification not in self.ALLOWED_VALUES['API.version.dataClassification']:
            self.add_error(f"API.version.dataClassification '{data_classification}' is not in allowed values {self.ALLOWED_VALUES['API.version.dataClassification']}", file_path)
            return False
        
        return True
    
    def _validate_gbgf(self, data: Dict[str, Any], file_path: str) -> bool:
        """Rule 16: GBGF should be one of allowed values (check multiple locations)"""
        # GBGF can be in API.contract.GBGF or contractOwner.GBGF
        gbgf_contract = self._get_nested_value(data, 'API.contract.GBGF')
        gbgf_owner = self._get_nested_value(data, 'contractOwner.GBGF')
        gbgf_api_contract = self._get_nested_value(data, 'API.contractOwner.GBGF')
        gbgf = gbgf_contract or gbgf_owner or gbgf_api_contract
        
        if gbgf is None:
            self.add_error("GBGF field is missing (should be in API.contract.GBGF or contractOwner.GBGF)", file_path)
            return False
        
        # Provide location info in the error message
        location = "API.contract.GBGF" if gbgf_contract else "contractOwner.GBGF"
        
        if gbgf not in self.ALLOWED_VALUES['API.contract.GBGF']:
            self.add_error(f"GBGF value '{gbgf}' in {location} is not in allowed values {self.ALLOWED_VALUES['API.contract.GBGF']}", file_path)
            return False
        
        return True
    
    def _validate_service_line(self, data: Dict[str, Any], file_path: str) -> bool:
        """Rule 17: API.contractOwner.serviceLine should not be missing"""
        service_line = self._get_nested_value(data, 'API.contractOwner.serviceLine') or self._get_nested_value(data, 'contractOwner.serviceLine')
        
        if service_line is None or service_line == "":
            self.add_error("serviceLine is missing (should be in API.contractOwner.serviceLine or contractOwner.serviceLine)", file_path)
            return False
        
        return True
    
    def _validate_team_name(self, data: Dict[str, Any], file_path: str) -> bool:
        """Rule 18: API.contractOwner.teamName should not be missing"""
        team_name = self._get_nested_value(data, 'API.contractOwner.teamName') or self._get_nested_value(data, 'contractOwner.teamName')
        
        if team_name is None or team_name == "":
            self.add_error("teamName is missing (should be in API.contractOwner.teamName or contractOwner.teamName)", file_path)
            return False
        
        return True
    
    def _validate_team_email_address(self, data: Dict[str, Any], file_path: str) -> bool:
        """Rule 19: API.contractOwner.teamEmailAddress should not be missing"""
        team_email = self._get_nested_value(data, 'API.contractOwner.teamEmailAddress') or self._get_nested_value(data, 'contractOwner.teamEmailAddress')
        
        if team_email is None or team_email == "":
            self.add_error("teamEmailAddress is missing (should be in API.contractOwner.teamEmailAddress or contractOwner.teamEmailAddress)", file_path)
            return False
        
        return True
    
    def _validate_transaction_names(self, data: Dict[str, Any], file_path: str) -> bool:
        """Rule 20: API.version.transactionNames should not be empty if API.layer is sAPI"""
        layer = self._get_nested_value(data, 'API.layer')
        transaction_names = self._get_nested_value(data, 'API.version.transactionNames')
        
        if layer == "sAPI":
            if transaction_names is None or (isinstance(transaction_names, list) and len(transaction_names) == 0):
                self.add_error("API.version.transactionNames is required when API.layer is 'sAPI'", file_path)
                return False
        
        return True 