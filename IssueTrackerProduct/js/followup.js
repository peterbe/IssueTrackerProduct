var modified_timestamp;
var _base_url = location.href.split(/[\?\#]/)[0];
if (_base_url.slice(-10)=='index_html')
  _base_url = _base_url.slice(0,-10);
if (_base_url.charAt(_base_url.length-1)=='/')
  _base_url = _base_url.substring(0, _base_url.length-1);


function checkRefresh() {
   if (!modified_timestamp) return false;
   $.get(_base_url+'/getModifyTimestamp',{}, function(resp) {
      if (resp && modified_timestamp && parseInt(resp) != parseInt(modified_timestamp)) {
         modified_timestamp = resp;
         $('#threads').load(_base_url+'/ShowIssueThreads?no_email_encoding=1');
         $('#issuedata').load(_base_url+'/ShowIssueData?no_email_encoding=1');
         if (document.title.indexOf("(automatically refreshed) ")==-1)
           document.title = "(automatically refreshed) " + document.title;
         refreshinterval = orig_refreshinterval;
         previous_clairvoyant_note = '';
      }
   });
}

function clearAutoRefreshTitle() {
  document.title = document.title.replace(/\(automatically refreshed\) /,'');
}
  
var previous_clairvoyant_note='';
var clairvoyant_timer;
var page_generated_timestamp, last_clairvoyant_check_timestamp;
function clairvoyant_followups() {
   var url = _base_url+'/getRecentOtherDraftThreadAuthor_json?nochache='+(Math.random()+"").substr(2, 5);
   
   if (last_clairvoyant_check_timestamp) {
      url += '&min_timestamp='+last_clairvoyant_check_timestamp;
   } else {
      if ($('input[name=page_generated_timestamp]').size())
        page_generated_timestamp = $('input[name=page_generated_timestamp]').val();
      if (page_generated_timestamp)
        url += '&min_timestamp='+page_generated_timestamp;
   }
   $.getJSON(url, {'only_fromname':1}, function(resp) {
      try {
         last_clairvoyant_check_timestamp = parseInt(new Date().getTime() / 1000);
	 if (resp && resp.msg && resp.msg != previous_clairvoyant_note) {
	    var previous_title = document.title;
	    $('#recent-draftthread-author').text(resp.msg);
            $('#recent-draftthread-author:hidden').fadeIn(300);
	    document.title = resp.msg + ' - ' + document.title;
	    previous_clairvoyant_note = resp.msg;
            if (clairvoyant_timer)
              clearTimeout(clairvoyant_timer);
	    clairvoyant_timer = setTimeout(function() {
	       $('#recent-draftthread-author:visible').fadeOut(500);
	       document.title = previous_title;
	    }, 10*1000);
	    clairvoyantinterval = orig_clairvoyantinterval;
	 }
      } catch(ex) {alert(ex);}
   });
}
var cf_timer;
var clairvoyantinterval,orig_clairvoyantinterval;
clairvoyantinterval=orig_clairvoyantinterval=7;
start_clairvoyant_followups = function() {
   clairvoyant_followups();
   cf_timer=window.setTimeout("start_clairvoyant_followups()", clairvoyantinterval*1000);
   clairvoyantinterval += 0.05;
}

var r_timer;
var refreshinterval,orig_refreshinterval;
refreshinterval=orig_refreshinterval=3;
function startautorefresh() {
   checkRefresh();
   r_timer=window.setTimeout(startautorefresh, refreshinterval*1000);
   refreshinterval += refreshinterval*0.007;
}

function toggleHighlight() {
   if ($('span.q_highlight').size()) {
      $('span.q_highlight').addClass('q_highlight-off').removeClass('q_highlight');
      $('a.highlight-toggle').removeClass('q_highlight').text('Turn on highlighting');
   } else {
      $('span.q_highlight-off').addClass('q_highlight').removeClass('q_highlight-off');
      $('a.highlight-toggle').addClass('q_highlight').text('Turn off highlighting');
   }
}

$(function() {
   
   setTimeout(function() {
      $.get(_base_url+'/getModifyTimestamp', {}, function(resp) {
	 if (resp) modified_timestamp = resp;
      });
   }, 3*1000);
   
   setTimeout(function() {
      startautorefresh();
   }, 5*1000);
   
   setTimeout(function() {
      start_clairvoyant_followups();
   }, 7*1010);   
   
   if ($('span.q_highlight').size() && $('a.backlink')) {
      // make a javascript link that removes the highlighting
      $('a.backlink').parent('div').append(
         $('<a>').attr('href','.').addClass('highlight-toggle').addClass('q_highlight')
                                           .click(function() {toggleHighlight();return false})
                                           .text('Turn off highlighting')
      );
   }
   
   $('#delete_option_button').attr('onclick','').attr('onkeypress','');
   $('#delete_option_button').click(function() {
      $('#optionbuttons-outer').load('form_delete');
      return false;
   });
});


function af(dest, e, ignoreword) {
  var val=dest.value;
  if (val.indexOf(e)==-1) {
    val = val.replace(ignoreword, "");
    if ($.trim(val).charAt($.trim(val).length-1)!=',') val = val+", ";
    val = val+e+", "
  } else {
    if (val.indexOf(e+", ")!=-1) {
      val = val.replace(e+", ", "");
    }
  }
  dest.value = val;  
}
function softsubmit(action) {
  if (document.form_followup) {
    document.form_followup.action.value=action;
    document.form_followup.submit();
  }
}


function showAssignmentForm() {
   $('#assignment-form-rest').show(300);
   $('#assignee').css('color','#000');
}

function hideAssignmentForm() {
   $('#assignment-form-rest').hide(300);
   $('#assignee').css('color','#666');
}

function closeAnnouncement() {
   $('table.announcement').hide();
   return false;
}

/* FEATURE ON HOLD
// If the AJAX doesn't work for some reason, pause the autorefresh for a
// very long time and show a little notice message. 
$(document).ajaxError(function(event, request, settings){
   clairvoyantinterval = refreshinterval = 60; //seconds
   alert(settings.url);
   showAJAXProblemWarning(settings.url);
});
 */

