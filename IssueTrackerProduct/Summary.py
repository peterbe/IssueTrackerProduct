
import datetime
from time import time
from pprint import pprint
import warnings
from Acquisition import aq_inner, aq_parent
from AccessControl import ClassSecurityInfo
from DateTime import DateTime
from zExceptions import NotFound

try:
    # >= Zope 2.12
    from App.class_init import InitializeClass
except ImportError:
    # < Zope 2.12
    from Globals import InitializeClass

from TemplateAdder import addTemplates2Class
from Constants import ISSUETHREAD_METATYPE

try:
    from collections import defaultdict
except:
    class defaultdict(dict):
        def __init__(self, default_factory=None, *a, **kw):
            if (default_factory is not None and
                not hasattr(default_factory, '__call__')):
                raise TypeError('first argument must be callable')
            dict.__init__(self, *a, **kw)
            self.default_factory = default_factory
        def __getitem__(self, key):
            try:
                return dict.__getitem__(self, key)
            except KeyError:
                return self.__missing__(key)
        def __missing__(self, key):
            if self.default_factory is None:
                raise KeyError(key)
            self[key] = value = self.default_factory()
            return value
        def __reduce__(self):
            if self.default_factory is None:
                args = tuple()
            else:
                args = self.default_factory,
            return type(self), args, None, None, self.items()
        def copy(self):
            return self.__copy__()
        def __copy__(self):
            return type(self)(self.default_factory, self)
        def __deepcopy__(self, memo):
            import copy
            return type(self)(self.default_factory,
                              copy.deepcopy(self.items()))
        def __repr__(self):
            return 'defaultdict(%s, %s)' % (self.default_factory,
                                            dict.__repr__(self))


MONTH_NAMES = [DateTime(2010, i+1, 1).strftime('%B')
               for i in range(12)]

#----------------------------------------------------------------------------

class ConfigurationError(Exception):
    pass

class SummaryBase(object):

    security = ClassSecurityInfo()

    def getSummaryPageTitle(self, month=None, year=None):
        month, year = self._get_and_check_month_and_year(month, year)
        return "Summary for %s, %s" % (month, year)

    def getSummaryPageURL(self, month=None, year=None):
        month, year = self._get_and_check_month_and_year(month, year)
        return self.getRootURL() + '/%s/%s' % (year, month)

    def getIssueSummaryByMonth(self, month=None, year=None):
        """return a list of issues grouped by statuses"""
        month, year = self._get_and_check_month_and_year(month, year)

        month_nr = MONTH_NAMES.index(month)+1
        start_date = DateTime(year, month_nr, 1)
        if month_nr == 12:
            end_date = DateTime(year + 1, 1, 1)
        else:
            end_date = DateTime(year, month_nr + 1, 1)

        trackers = [self] + self._getBrothers()


        base_search = {'meta_type':'Issue Tracker Issue'}

        added_issues = []

        # keys status, values list of issue objects
        modified_issues = defaultdict(list)

        for tracker in trackers:
            catalog = tracker.getCatalog()

            _has_issuedate_index = catalog._catalog.indexes.has_key('issuedate')

            if _has_issuedate_index:
                search = dict(base_search,
                              issuedate={'query': [start_date, end_date],
                                         'range':'min:max'})
            else:
                search = dict(base_search)

            for brain in catalog(sort_on=_has_issuedate_index and 'issuedate' or 'modifydate',
                                 **search):
                try:
                    issue = brain.getObject()
                except KeyError:
                    warnings.warn("ZCatalog (%s) out of date. Press Update Everything" %\
                                  catalog.absolute_url_path())
                    continue
                if not _has_issuedate_index:
                    # we have to manually filter it
                    if issue.getIssueDate() < start_date:
                        continue
                    if issue.getIssueDate() > end_date:
                        continue

                added_issues.append(issue)

            search = dict(base_search,
                          modifydate={'query': [start_date, end_date],
                                      'range':'min:max'})
            for brain in catalog(sort_on='modifydate', **search):
                try:
                    issue = brain.getObject()
                except KeyError:
                    warnings.warn("ZCatalog (%s) out of date. Press Update Everything" %\
                                  catalog.absolute_url_path())
                    continue
                if issue.getIssueDate() == issue.getModifyDate():
                    continue

                # now we need to find the thread that made this status change
                for thread in sorted(issue.getThreadObjects(),
                                     lambda x,y: cmp(y.threaddate, x.threaddate)):
                    # XXX:
                    # A thought would be to include all threads where there is a change
                    # Food for thought

                    if thread.getTitle().lower().startswith('changed status'):
                        break
                else:
                    # the issue doesn't have any threads!
                    continue

                modified_issues[issue.getStatus()].append((issue, thread))

        # next we need to flatten the dict modified_issues by the order statuses
        # are defined
        statuses = [x[0] for x in self.getStatusesMerged(aslist=True)]
        def sorter_by_status(x, y):
            try:
                i = statuses.index(x[0])
            except ValueError:
                i = -1
            try:
                j = statuses.index(y[0])
            except ValueError:
                j = -1
            return cmp(i, j)

        modified_issues = sorted(modified_issues.items(), sorter_by_status)

        # clear some memory
        trackers = None
        return dict(added_issues=added_issues,
                    modified_issues=modified_issues)


    def getPrevNextMonthURLs(self, month=None, year=None):
        month, year = self._get_and_check_month_and_year(month, year)

        month_nr = MONTH_NAMES.index(month)+1
        date = datetime.date(year, month_nr, 1)
        prev_date = date - datetime.timedelta(days=1)
        next_date = date + datetime.timedelta(days=31) # e.g. Jan 1 + 31 days is some time in Feb

        if self.absolute_url_path() == '/':
            prev_url = prev_date.strftime('/%Y/%B')
        else:
            prev_url = self.absolute_url_path() + prev_date.strftime('/%Y/%B')

        if next_date > datetime.date.today():
            next_url = None
        else:
            if self.absolute_url_path() == '/':
                next_url = next_date.strftime('/%Y/%B')
            else:
                next_url = self.absolute_url_path() + next_date.strftime('/%Y/%B')
        return prev_url, next_url


    def _get_and_check_month_and_year(self, month, year):
        if month is None:
            month = DateTime().strftime('%B')
            year = DateTime().year()

        if month not in MONTH_NAMES:
            raise NotFound("Unrecognized month name")
        try:
            year = int(year)
        except ValueError:
            raise NotFound("Unrecognized year number")

        return month, year

    def getUniqueIssueClassname(self, issue):
        """the reason this method is necessary is because we can't construct a
        class name (for the HTML) based on just the issue ID since that's only
        unique per issuetracker. If you use brother issuetrackers your page
        might eventually feature both issue foo/010 and bar/020.

        I could make this unique class name depend on the parent the issue is
        in but if the issue is in a BTreeFolder I have to use aq_parent more
        than once and it gets messy.
        """
        return "i%s-%s" % (issue.getId(), int(issue.getIssueDate()))

    def isFirstStatusOption(self, status):
        for option in [x[0] for x in self.getStatusesMerged(aslist=True)]:
            if option.lower() == status.lower():
                return True
            return False

    def isLastStatusOption(self, status):
        for option in reversed([x[0] for x in self.getStatusesMerged(aslist=True)]):
            if option.lower() == status.lower():
                return True
            return False

    def getIssueActivity(self, month=None, year=None):
        month, year = self._get_and_check_month_and_year(month, year)
        month_nr = MONTH_NAMES.index(month)+1
        start_date = DateTime(year, month_nr, 1)
        if month_nr == 12:
            end_date = DateTime(year + 1, 1, 1)
        else:
            end_date = DateTime(year, month_nr + 1, 1)

        trackers = [self] + self._getBrothers()
        base_search = {'meta_type': ISSUETHREAD_METATYPE}

        issues = []
        issue_info = {}
        _use_followup_actual_time = self.UseFollowupActualTime()
        for tracker in trackers:
            catalog = tracker.getCatalog()
            if not catalog._catalog.indexes.has_key('threaddate'):
                raise ConfigurationError(
                "Can't sum followup actual time without threaddate. Run UpdateEverything()")
            search = dict(base_search,
                          threaddate={'query': [start_date, end_date],
                                     'range':'min:max'})
            for brain in catalog(**search):
                try:
                    thread = brain.getObject()
                except KeyError:
                    warnings.warn("ZCatalog (%s) out of date. Press Update Everything" %\
                                  catalog.absolute_url_path())
                    continue

                issue = aq_parent(aq_inner(thread))
                if issue not in issues:
                    issues.append(issue)
                info = issue_info.get(issue.absolute_url_path(), {})
                info['followups'] = info.get('followups', 0) + 1
                info['actual_time'] = info.get('actual_time', 0.0)

                if _use_followup_actual_time and thread.getActualTimeHours():
                    info['actual_time'] += thread.getActualTimeHours()

                issue_info[issue.absolute_url_path()] = info

        return [(issue, issue_info[issue.absolute_url_path()])
                for issue in issues]


    def getTotalActualFollowupHours(self, month=None, year=None):
        assert self.UseFollowupActualTime()
        month, year = self._get_and_check_month_and_year(month, year)
        month_nr = MONTH_NAMES.index(month)+1
        start_date = DateTime(year, month_nr, 1)
        if month_nr == 12:
            end_date = DateTime(year + 1, 1, 1)
        else:
            end_date = DateTime(year, month_nr + 1, 1)

        trackers = [self] + self._getBrothers()
        base_search = {'meta_type': ISSUETHREAD_METATYPE}

        total = 0.0
        #threads = list()

        for tracker in trackers:
            catalog = tracker.getCatalog()

            _has_threaddate_index = catalog._catalog.indexes.has_key('threaddate')

            if _has_threaddate_index:
                search = dict(base_search,
                              threaddate={'query': [start_date, end_date],
                                         'range':'min:max'})
            else:
                search = dict(base_search)
                raise ConfigurationError(
                "Can't sum followup actual time without threaddate. Run UpdateEverything()")

            for brain in catalog(**search):
                try:
                    thread = brain.getObject()
                except KeyError:
                    warnings.warn("ZCatalog (%s) out of date. Press Update Everything" %\
                                  catalog.absolute_url_path())
                    continue
                if not thread.getActualTimeHours():
                    continue

                if not _has_threaddate_index:
                    # we have to manually filter it
                    if thread.getThreadDate() < start_date:
                        continue
                    if issue.getThreadDate() > end_date:
                        continue

                total += thread.getActualTimeHours()
                #threads.append(thread)

        #count_threads = len(threads)
        return total


zpts = (
        'zpt/show_summary',
        )



addTemplates2Class(SummaryBase, zpts, extension='zpt')

InitializeClass(SummaryBase)
