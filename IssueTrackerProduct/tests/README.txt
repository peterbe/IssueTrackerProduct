You might want to set this so you don't try to send out emails:
export DEBUG_ISSUETRACKERPRODUCT=1

You might want to disable CheckoutableTemplates:
export DISABLE_CHECKOUTABLE_TEMPLATES=1

To run all IssueTracker tests
./bin/zopectl test --dir Products/IssueTrackerProduct/tests/

To just run testIssueTracker.py
./bin/zopectl test --dir Products/IssueTrackerProduct/tests/ --tests-pattern=testIssueTracker

To just run testIssueTracker.py but only test called test_debatingIssue()
./bin/zopectl test --dir Products/IssueTrackerProduct/tests/ --tests-pattern=testIssueTracker --test=test_debatingIssue


Include --keepbytecode when the set of tests gets large. At the time of
writing, this doesn't make any difference to the time it takes.