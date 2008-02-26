function refreshActivityTable() {
   $('#table-outer').load('show_activity_table?nocache='+(Math.random()+"").substr(2, 5));
}

$(function() {
   $('#tree').treeview({
      animated:300,
      persist:"cookie"
   });
   
   $('li.ignored').each(function() {
      $('span.folder', this)
        .fadeTo(0, 0.3);
      $('span.file', this)
        .fadeTo(0, 0.3);      
   });
});


