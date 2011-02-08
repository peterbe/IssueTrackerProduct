// Useful functions for Adding issue
function askNoti(checkit, youare) { 
   var el = $('#asi-noti');
   var extrahtml = "<input type=\"checkbox\" name=\"notify-assignee\" ";
   if (checkit != youare) extrahtml += "checked=\"checked\" ";
   extrahtml += "value=\"1\"/>";
   extrahtml += "Send notification to assignee";
   extrahtml += "<input type=\"hidden\" name=\"asked-notify-assignee\" value=\"1\"/>";
   el.html(extrahtml);
}

function shownewsection() {
   $('#sections').attr('size', parseInt($('#sections').attr('size')) - 1);
   $('#newsection').show();
}
function autosave() {
   $.post('AutoSaveDraftIssue', $(document.ai).fastSerialize(),
          function(resp) {
             if (resp) {
                $('input[name="draft_issue_id"]').val(resp);
             }
          });
}

var as_timer;
var stopautosave = function() {  
  if (as_timer) clearTimeout(as_timer);
};
var startautosave = function() {
  autosave(); 
  as_timer = window.setTimeout("startautosave()", AUTO_SAVE_INTERVAL * 1000);
};

function deldraft(draftid) {
   $('p.draft-'+draftid).remove();
   $.post('DeleteDraftIssue', {id:draftid, return_show_drafts_simple:1}, function(resp) {
      $('#issuedraftsouter').html(resp);
   });
   return false;  
}
