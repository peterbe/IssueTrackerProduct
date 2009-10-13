// This script won't work unless issuenotes-core.js is loaded
//

function cancelSaveNote(form, issue_identifier, thread_identifier) {
   if (thread_identifier) 
      $('a.new-note', '.ihead').qtip('hide');  // hide all
   else 
      $('a.new-note', '.ihead').qtip('hide');
}

function new_note(element, thread_identifier) {
   var jelement = $(element);
   if (thread_identifier) {
     var issue_identifier = jelement.parents('tr.issue').attr('id');
   } else
     var issue_identifier = jelement.parents('tr.issue').attr('id');
   var options = _qtip_options(jelement, issue_identifier, thread_identifier, 'left');
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