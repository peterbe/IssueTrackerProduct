// Useful functions for Quick Add Issue


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
   as_timer=window.setTimeout("startautosave()", AUTO_SAVE_INTERVAL * 1000);
};


function softsubmit() {
  if (document.ai) {
    document.ai.action='<dtml-var getRootURL>/AddIssue';
    document.ai.submit();
  }
}