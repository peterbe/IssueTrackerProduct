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
   
   //$.post(ROOT_URL + '/getIssueNotes_json', {ids:issue_identifiers}, function(notes) {
   //   $.each(notes, function(i, note) {
   //      __show_note(note.issue_identifier, note);
   //   });
   //}, "json");      

   
   // Create the modal backdrop on document load so all modal tooltips can use it
   $('<div id="qtip-blanket">')
      .css({
         position: 'absolute',
         top: $(document).scrollTop(), // Use document scrollTop so it's on-screen even if the window is scrolled
         left: 0,
         height: $(document).height(), // Span the full document height...
         width: '100%', // ...and full width

         opacity: 0.7, // Make it slightly transparent
         backgroundColor: 'black',
         zIndex: 5000  // Make sure the zIndex is below 6000 to keep it below tooltips!
      })
      .appendTo(document.body) // Append to the document body
      .hide(); // Hide it initially
   
});