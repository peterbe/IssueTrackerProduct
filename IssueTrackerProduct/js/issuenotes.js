// This script won't work unless issuenotes-core.js is loaded
// 
function new_note(element, thread_identifier) {
   var jelement = $(element);
   if (thread_identifier) {
     var issue_identifier = $('div.issue', jelement.parents('div.issue-and-threads')).attr('id');
   } else
     var issue_identifier = jelement.parents('div.issue').attr('id');
   var options = _qtip_options(jelement, issue_identifier, thread_identifier);
   options.show = { when: 'click', ready: true, solo: true };
   jelement.qtip(options);
   return false;
}
 
$(function () {
  
   $('a.old-note').each(function(i, e) {
      $(e).qtip(_qtip_options_by_title($(this)));
      $(e).attr('title','');
   }).click(function() {
      return false;
   });
   
   
});