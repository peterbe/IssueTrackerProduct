// This script won't work unless issuenotes-core.js is loaded
$(function () {
  
   var issue_identifier;
   var thread_identifier;
   var issue_identifiers = new Array();
   var block;
   
   $('div.issue-and-threads').each(function() {
      block = this;
      $('div.issue', this).each(function() {
         issue_identifier = $(this).attr('id');
         issue_identifiers.push(issue_identifier);
         
         $('div.ihead', this).prepend($('<a href="#"></a>').click(function() {
            return false;
         }).addClass('new-note').attr('title', 'Click to add a new note')
                                      .append($('<img>')
                                              .attr('src','/misc_/IssueTrackerProduct/new-issuenote.png')
                                              .attr('border','0')
                                              .attr('alt','New note')
                                              ).qtip(_qtip_options($(this), issue_identifier, null))
                                      );
         
         $('div.threadbox', block).each(function() {
            thread_identifier = $(this).attr('id');
            $('div.thead', this).prepend($('<a href="#"></a>').click(function() {
               return false;
            }).addClass('new-note').attr('title', 'Click to add a new note')
                                         .append($('<img>')
                                                 .attr('src','/misc_/IssueTrackerProduct/new-issuenote.png')
                                                 .attr('border','0')
                                                 .attr('alt','New note')
                                                 ).qtip(_qtip_options($(this), issue_identifier, thread_identifier))
                                         );
         });
      });
   });
   
   if (issue_identifiers.length > 1) {
      $.post(ROOT_URL + '/getIssueNotes_json', {ids:issue_identifiers}, function(notes) {
         $.each(notes, function(i, note) {
            __show_note(note.issue_identifier, note);
         });
      }, "json");      
   } else {
      $.getJSON(ROOT_URL + '/getIssueNotes_json', {ids:issue_identifiers}, function(notes) {
         $.each(notes, function(i, note) {
            __show_note(note.issue_identifier, note);
         });
      });
   }

   
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