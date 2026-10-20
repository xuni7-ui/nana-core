"""Explicit offline regression selection; never selects opt-in live providers."""
import argparse,subprocess,sys
FAST_FOUNDATION_REGRESSION=(
 'tests/first_life_hardening','tests/first_life/test_durability.py',
 'tests/cloud_life/test_provider_budget.py','tests/cloud_life/test_operations.py',
 'tests/provider_routing/test_router.py','tests/continuous_runtime/test_storage_runtime.py',
 'tests/open_autonomy/test_code_skills.py','tests/continuous_self/test_privacy.py',
 'tests/affective_autonomy/test_governance.py','tests/controlled_hands/test_recovery.py')
FULL_FOUNDATION_REGRESSION=('tests',)
# Change selection is a recommendation, never a substitute for final regression.
CHANGE_SUITES={
 'life/durability.py':('tests/first_life/test_durability.py','tests/first_life_hardening/test_atomic_recovery.py'),
 'continuity/privacy.py':('tests/continuous_self/test_privacy.py','tests/affective_autonomy/test_relationship_privacy.py','tests/cloud_life/test_operations.py'),
 'continuity/hands/':('tests/controlled_hands','tests/cloud_life/test_daily_tasks.py'),
 'life/inspector.py':('tests/first_life_hardening/test_inspector.py',),
 'life/control.py':('tests/cloud_life','tests/first_life/test_review.py')}

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('suite',choices=('fast','full'));p.add_argument('--junitxml');a=p.parse_args()
 args=[sys.executable,'-m','pytest',*(FAST_FOUNDATION_REGRESSION if a.suite=='fast' else FULL_FOUNDATION_REGRESSION),'-q']
 if a.junitxml:args+=['-o','junit_family=xunit1','--junitxml='+a.junitxml]
 raise SystemExit(subprocess.run(args,check=False).returncode)
if __name__=='__main__':main()
