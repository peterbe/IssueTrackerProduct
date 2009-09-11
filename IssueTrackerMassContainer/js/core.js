var since_timestamp = (new Date).getTime()/1000;

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
   
   $.get('show_recent_activity_tbodies?since='+since_timestamp, function(res) {
      if ($.trim(res)) {
         var table = $('#activity-table');
         $('thead', '#activity-table').after(res);
      }
      _hideLoading();
      
      since_timestamp = (new Date).getTime()/1000;
   });
}

function autorefreshActivityTable() {
   refreshActivityTable();
   window.setTimeout(function() {
      autorefreshActivityTable();
   }, 1000*60);
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
   
   window.setTimeout(function() {autorefreshActivityTable()}, 1000*60);
   
});



