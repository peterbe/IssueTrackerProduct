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
   // only go ahead if the Loading is or was hidden (needs testing)
   if ($('a:hidden', '#table-refresher').length) return false;
   
   _showLoading();
   
   $.get('show_recent_activity_tbodies?since='+since_timestamp, function(res) {
      if ($.trim(res)) {
         var table = $('#activity-table');
         $('thead', '#activity-table').after(res);
	 refresh_interval = orig_refresh_interval;
      }
      _hideLoading();
      
      since_timestamp = (new Date).getTime()/1000;
   });
   return true;
}

var orig_refresh_interval = refresh_interval = 30;
function autorefreshActivityTable() {
   refreshActivityTable();
   refresh_interval += 5; // seconds to added every time
   window.setTimeout(function() {
      autorefreshActivityTable();
   }, refresh_interval * 1000);
}

$(function() {
   var collapsed = $('li.folder', 'ul#tree').length > 3;
   $('#tree').treeview({
      animated:300,
      persist:"cookie",
      collapsed: collapsed
   });
   
   $('li.ignored').each(function() {
      $('span.folder', this)
        .fadeTo(0, 0.3);
      $('span.file', this)
        .fadeTo(0, 0.3);      
   });
   
   window.setTimeout(function() {autorefreshActivityTable()}, 1000*60);
   
});



