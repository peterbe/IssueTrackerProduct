// This script won't work unless issuenotes-core.js is loaded
//
$(function () {
  
   var issue_identifier;
   var thread_identifier;
   var issue_identifiers = new Array();

   $('tr.issue', 'table').each(function() {
      issue_identifier = $(this).attr('id');
      issue_identifiers.push(issue_identifier);
         
      $('td.ihead', this).append($('<a href="#"></a>').click(function() {
         return false;
      }).addClass('new-note').attr('title', 'Click to add a new note')
                                      .append($('<img>')
                                              .attr('src','/misc_/IssueTrackerProduct/new-issuenote.png')
                                              .attr('border','0')
                                              .attr('alt','New note')
                                              ).qtip(_qtip_options($(this), issue_identifier, null))
                                      );
         
   });
   
   $.post(ROOT_URL + '/getIssueNotes_json', {ids:issue_identifiers}, function(notes) {
      $.each(notes, function(i, note) {
         __show_note(note.issue_identifier, note, 'td');
      });
   }, "json");      
   
});