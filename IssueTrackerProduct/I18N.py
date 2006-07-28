#try:
#    from Products.PlacelessTranslationService.MessageID import MessageIDFactory
#    _ = MessageIDFactory('itp')
#except ImportError:
#    def _(s):
#  return s

def _(s, *a, **k):
    return s