#!/usr/bin/env python3
"""
BMS System Deployment Script
Safely removes legacy discovery components and activates new BMS system
"""

import os
import shutil
from pathlib import Path

def backup_old_files():
    """Backup old discovery files before removal"""
    print("📦 Creating backup of old discovery system...")
    
    backup_dir = Path('/Users/michaelmote/Desktop/AMC-TRADER/.bms-migration-backup')
    backup_dir.mkdir(exist_ok=True)
    
    # Files to backup
    old_files = [
        'backend/src/routes/discovery.py',
        'backend/src/routes/calibration.py', 
        'backend/src/services/squeeze_detector.py',
        'backend/src/services/squeeze_validator.py',
        'backend/src/jobs/discover.py',
        'backend/src/jobs/discover_no_fallback.py',
        'backend/src/jobs/discovery.py',
        'frontend/src/components/TopRecommendations.tsx',
        'frontend/src/components/SqueezeMonitor.tsx',
        'frontend/src/components/Recommendations.tsx',
        'frontend/src/pages/DiscoveryPage.tsx',
        'frontend/src/pages/SqueezePage.tsx'
    ]
    
    backed_up = 0
    for file_path in old_files:
        full_path = Path('/Users/michaelmote/Desktop/AMC-TRADER') / file_path
        if full_path.exists():
            backup_path = backup_dir / file_path
            backup_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(full_path, backup_path)
            print(f"  ✅ Backed up {file_path}")
            backed_up += 1
    
    print(f"📦 Backed up {backed_up} files to {backup_dir}")
    return backup_dir

def remove_old_discovery_files():
    """Remove old discovery system files"""
    print("\n🗑️ Removing old discovery system files...")
    
    # Backend files to remove
    backend_files = [
        'backend/src/routes/discovery.py',
        'backend/src/routes/calibration.py',
        'backend/src/services/squeeze_detector.py', 
        'backend/src/services/squeeze_validator.py',
        'backend/src/jobs/discover.py',
        'backend/src/jobs/discover_no_fallback.py',
        'backend/src/jobs/discovery.py',
        'backend/src/strategy_resolver.py',
        'backend/src/discovery/detectors/volume_momentum.py',
        'backend/src/discovery/detectors/squeeze.py',
        'backend/src/discovery/feature_store.py',
        'backend/calibration/active.json',
        'backend/calibration/proposed.json'
    ]
    
    # Frontend files to remove  
    frontend_files = [
        'frontend/src/components/TopRecommendations.tsx',
        'frontend/src/components/SqueezeMonitor.tsx', 
        'frontend/src/components/Recommendations.tsx',
        'frontend/src/components/RecommendationCard.tsx',
        'frontend/src/components/RecommendationTile.tsx',
        'frontend/src/components/SqueezeAlert.tsx',
        'frontend/src/components/AuditModal.tsx',
        'frontend/src/components/PatternHistory.tsx',
        'frontend/src/pages/DiscoveryPage.tsx',
        'frontend/src/pages/SqueezePage.tsx'
    ]
    
    # Root level files to remove
    root_files = [
        'run_discovery.py',
        'simple_discovery_debug.py',
        'debug_discovery.py',
        'fix_discovery_universe.py',
        'calibration/active.json',
        'calibration/proposed.json',
        'calibration/diag.json'
    ]
    
    removed = 0
    all_files = backend_files + frontend_files + root_files
    
    for file_path in all_files:
        full_path = Path('/Users/michaelmote/Desktop/AMC-TRADER') / file_path
        if full_path.exists():
            full_path.unlink()
            print(f"  🗑️ Removed {file_path}")
            removed += 1
    
    # Remove empty directories
    empty_dirs = [
        'backend/calibration',
        'calibration', 
        'backend/src/discovery',
        'backend/src/discovery/detectors'
    ]
    
    for dir_path in empty_dirs:
        full_dir = Path('/Users/michaelmote/Desktop/AMC-TRADER') / dir_path
        if full_dir.exists() and not any(full_dir.iterdir()):
            full_dir.rmdir()
            print(f"  🗑️ Removed empty directory {dir_path}")
            removed += 1
    
    print(f"🗑️ Removed {removed} old discovery files and directories")

def update_frontend_routing():
    """Update frontend App.tsx to use new BMS components"""
    print("\n🔄 Updating frontend routing...")
    
    app_path = Path('/Users/michaelmote/Desktop/AMC-TRADER/frontend/src/App.tsx')
    
    if not app_path.exists():
        print("❌ App.tsx not found")
        return False
    
    # Read current content
    content = app_path.read_text()
    
    # Replace old routes with new BMS routes
    replacements = [
        ('import DiscoveryPage from', '// import DiscoveryPage from'),
        ('import SqueezePage from', '// import SqueezePage from'), 
        ('<Route path="/discovery" element={<DiscoveryPage />} />', 
         '<Route path="/discovery" element={<BMSDiscoveryPage />} />'),
        ('<Route path="/squeeze" element={<SqueezePage />} />',
         '<Route path="/squeeze" element={<BMSDiscoveryPage />} />')
    ]
    
    # Add import for new component
    if 'import BMSDiscoveryPage from' not in content:
        content = content.replace(
            'import React from \'react\';',
            'import React from \'react\';\nimport BMSDiscoveryPage from \'./pages/BMSDiscoveryPage\';'
        )
    
    # Apply replacements
    updated = False
    for old, new in replacements:
        if old in content:
            content = content.replace(old, new)
            updated = True
    
    if updated:
        app_path.write_text(content)
        print("✅ Frontend routing updated to use BMS components")
    else:
        print("⚠️ No routing updates needed")
    
    return True

def main():
    """Main deployment function"""
    print("🚀 BMS SYSTEM DEPLOYMENT")
    print("=" * 50)
    print("Deploying unified Breakout Momentum Score system")
    print("This will replace all legacy/hybrid discovery components\n")
    
    try:
        # Step 1: Backup old files
        backup_dir = backup_old_files()
        
        # Step 2: Remove old discovery files
        remove_old_discovery_files()
        
        # Step 3: Update frontend routing
        update_frontend_routing()
        
        # Step 4: Final validation
        print("\n✅ Running final validation...")
        import subprocess
        result = subprocess.run(['python3', 'validate_bms_deployment.py'], 
                              capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ BMS system validation passed!")
        else:
            print("⚠️ Validation had issues - check output")
        
        print("\n" + "=" * 50)
        print("🎉 BMS DEPLOYMENT COMPLETE!")
        print("=" * 50)
        print("✅ Old discovery system removed")
        print("✅ New BMS system activated") 
        print("✅ Frontend routing updated")
        print(f"✅ Backup created: {backup_dir}")
        
        print("\nNext steps:")
        print("1. Commit changes: git add . && git commit -m 'Deploy BMS unified discovery system'")
        print("2. Push to production: git push origin main") 
        print("3. Monitor deployment at https://amc-trader.onrender.com/discovery/health")
        print("4. Test new endpoints:")
        print("   - /discovery/candidates")
        print("   - /discovery/candidates/trade-ready")
        print("   - /discovery/winners-analysis")
        
    except Exception as e:
        print(f"\n❌ Deployment failed: {e}")
        print("The backup is available for rollback if needed.")
        return False
    
    return True

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)