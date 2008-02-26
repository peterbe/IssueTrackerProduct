$(function() {
   $('#tree').treeview({
      animated:300,
      persist:"cookie"
   });
   
   $('li.ignored').each(function() {
      $('span.folder', $(this))
        .fadeTo(0, 0.3);
      
   });
});

