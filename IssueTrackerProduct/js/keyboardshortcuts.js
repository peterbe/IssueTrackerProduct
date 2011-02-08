var keyboard_shortcuts_enabled = true;

function disableKS(e) {
   keyboard_shortcuts_enabled = false; 
}
function enableKS(e) { 
   keyboard_shortcuts_enabled = true; 
}

var curr_ilink_idx=-1;
var all_ilinks = new Array();
var prev_keycode;
var num_keycode=""; //numeric keycode
function body_onkeypress(evt){
    if (!keyboard_shortcuts_enabled) return;
    function S(k) { return String.fromCharCode(k); }
    if (window.event) key=window.event.keyCode;
    else key=evt.which;

    var s = S(key).toLowerCase();
    if (prev_keycode) prev_s = S(prev_keycode).toLowerCase();
    else prev_s = "";

    var burl = ROOT_RELATIVE_URL;
    if (s != 'g' && prev_s=='g'){
        
        if (s=='h') {
            location.href=burl+'/'; return false;
        } else if (s=='a') { //65 = a
            location.href=burl+'/AddIssue'; return false;
        } else if (s=='q') { // 81 = q
	    location.href=burl+'/QuickAddIssue'; return false;
        } else if (s=='l') { // 76 = l
            location.href=burl+'/ListIssues'; return false;
        } else if (s == 'c') { // 67 = c
            location.href=burl+'/CompleteList'; return false;
        } else if (s == 'u') { // 85 = u
            location.href=burl+'/User'; return false;
        } else if (s == 'r') { 
            location.href=burl+'/Reports'; return false;
            
        } else if (s == 's') { 
            location.href=burl+'/Statistics'; return false;
	     
	} else if (s == 'd') {
	   // Compare!
	   if (!$('#issuedata').size()) {
	      alert("Go to the issue first to compare");
	      return false;
	   }
	   var issue = prompt("Compare issues - Enter issue number:","");
	   if (issue !== null) {
	      var issueid = __getIssueID(issue);
	      if (issueid) 
		location.href=location.href.split('?')[0]+'?compareTo='+issueid;
	      else
		alert("Invalid Issue ID");
	   }
	   return false;	     
	   
        }       
        
    } else if (s == '#') { // 51 = #
       var issue = prompt("Enter issue number or title:","");
       if (issue !== null) {
         var issueid = __getIssueID(issue);
         if (issueid) {
             location.href=burl+'/'+issueid;
             return false;
           } else {
             location.href=ROOT_RELATIVE_URL + '/' + WHICH_LIST + '?search_only_on=title&q='+escape(issue);
           }
         }


    } else if (s=='n') {
	if (all_ilinks.length>1) {
	  if (curr_ilink_idx==-1) 
	     curr_ilink_idx=0;
	  else {
	     unhighlightILink(all_ilinks[curr_ilink_idx]);
	     curr_ilink_idx = (curr_ilink_idx+1) % all_ilinks.length;
	  }
	  highlightILink(all_ilinks[curr_ilink_idx]);
	} 
        
    } else if (s=='p') {
        if (all_ilinks.length>1) {
	  if (curr_ilink_idx==-1) 
	     curr_ilink_idx=all_ilinks.length-1;
	  else {
	     unhighlightILink(all_ilinks[curr_ilink_idx]);
	     curr_ilink_idx = (curr_ilink_idx-1) % all_ilinks.length;
	  }
	  highlightILink(all_ilinks[curr_ilink_idx]);
	}
       
    } else if (s=='s' || s=='/') {
        window.scrollTo(0,0);
	disableKS();
        $('#q').focus();
	$('#q').select();
    } 

    prev_keycode=key;
    return true;
}


function __getIssueID(issue) {
   var issueid = issue.replace(/^\s+|\s+$/g,'');
   var ok_id;
   if (ISSUE_PREFIX)
     ok_id = new RegExp('^\d+$|/^'+ ISSUE_PREFIX +'\d+$');
   else
     ok_id = new RegExp(/^\d+$|^#\d+$/);
   
  if (issueid) {
    if (ok_id.exec(issueid)) {
      if (issueid.length!=RANDOM_ID_LENGTH)
        while(issueid.length < RANDOM_ID_LENGTH)
          issueid = "0"+issueid;
      if (issueid[0]=='#') issueid = issueid.substring(1, issueid.length);
    }
    return issueid;
  } 
  return null;
}

$(document).bind("keypress", body_onkeypress);

function toggleInputsKS() {
   $("input,textarea,select").bind("blur", enableKS).bind("focus", disableKS);
}

function findILinks() {
   var c=0;
   $('a.ilink').each(function() {
      all_ilinks.push(this);
   });
}

function highlightILink(el){
   if (el) {
      el.innerHTML = '&gt;' + el.innerHTML;
      el.focus();
   }
}
function unhighlightILink(el){
   if (el) {
      var s = el.innerHTML;
      el.innerHTML = el.innerHTML.substring(4);
   }
}

$(function() {
   toggleInputsKS();
   findILinks();
});



