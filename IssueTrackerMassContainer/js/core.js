function _showLoading() {
   $('#table-refresher a').hide();
   $('#table-refresher').append($('<img>')
                                .addClass('loading-bar')
                                .attr('src','/misc_/IssueTrackerMassContainer/loading-bar.gif')
                                .attr('width','180')
                                .attr('height','14')
                                .attr('alt','Loading...'));
}
function _hideLoading() {
   $('img.loading-bar', $('#table-refresher')).remove();
   $('#table-refresher a').show();
   
}
function refreshActivityTable() {
   _showLoading();
   $('#table-outer').load('show_activity_table?nocache='+(Math.random()+"").substr(2, 5), function() {
      _hideLoading();
   });
}

function autorefreshActivityTable() {
   refreshActivityTable();
   window.setTimeout(function() {
      autorefreshActivityTable();
   }, 1000*30);
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
   
   window.setTimeout(function() {autorefreshActivityTable()}, 1000*30);
   
});



