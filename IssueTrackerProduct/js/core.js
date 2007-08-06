// from http://ejohn.org/projects/flexible-javascript-events/
function addEvent(obj, type, fn) { 
  if (obj.attachEvent) {
    obj["e"+type+fn] = fn;
    obj[type+fn] = function() { obj["e"+type+fn]( window.event ); }
    obj.attachEvent("on"+type, obj[type+fn]);
  } else
    obj.addEventListener(type, fn, false);
    
}

// from http://ejohn.org/projects/flexible-javascript-events/
function removeEvent(obj, type, fn) {
  if (obj.detachEvent) {
    obj.detachEvent("on"+type, obj[type+fn]);
    obj[type+fn] = null;
  } else
    obj.removeEventListener(type, fn, false);
}

//function $() {
//  var elements = new Array();
//  for (var i=0; i < arguments.length; i++) {
//    var element = arguments[i];
//    if (typeof element == 'string')
//      element=document.getElementById(element);
//    if (arguments.length == 1) 
//      return element;
//    elements.push(element);
//  }
//  return elements;
//}

$.id=function(id){return document.getElementById(id)};

function stripSpaces(x) {
   return $.trim(x);
}

function econvert(s) {
return s.replace(/%7E/g,'~').replace(/%28/g,'(').replace(/%29/g,')').replace(/%20/g,' ').replace(/_dot_| dot |_\._|\(\.\)/gi, '.').replace(/_at_|~at~/gi, '@');}

$(function() {
   $("a.aeh").each(function() {
      this.href = econvert(this.href);
      this.innerHTML = econvert(this.innerHTML);
   });
   $("span.aeh").each(function() {
      this.innerHTML = econvert(this.innerHTML);
   });
   
   // First, for all the textareas that have lots of lines of text 
   // in them, we want to double their number of rows
   $('textarea.autoexpanding').each(function() {
      console.log($.trim(this.value).split('\n').length);
      while ($.trim(this.value).split('\n').length > parseInt(this.rows))
        this.rows = '' + Math.round((parseInt(this.rows) * 1.5));
   });
            
   // When a user enters new lines, if they have entered more
   // lines than the textarea has rows, then double the textareas rows
   $('textarea.autoexpanding').bind('keyup', function() {
      if ($.trim(this.value).split('\n').length > parseInt(this.rows))
        this.rows = '' + Math.round((parseInt(this.rows) * 1.5));
   });
   
});


function G(p) {
  location.href=p;
}

function checkCaptchaValue(elm, msg, maxlength) {
   var v = $.trim(elm.value);
   if (v) {
      if (v.search(/\D/)>-1)
        alert(msg);
      //alert(v);
      //alert(typeof v);
      v = v.replace(/\D/g,'');
      if (v.length >= maxlength) 
        v = v.substring(0, maxlength);
      //elm.value = v;
   }
   return v;
}
function checkCaptchaValue(v, msg, maxlength) {
   v = $.trim(""+v);
   if (v) {
      if (v.search(/\D/)>-1)
        alert(msg);
      v = v.replace(/\D/g,'');
      if (v.length >= maxlength) 
        v = v.substring(0, maxlength);
   }
   return v;
}

$.fn.fastSerialize = function() {
    var a = [];

    $('input,textarea,select,button', this).each(function() {
        var n = this.name;
        var t = this.type;

        if ( !n || this.disabled || t == 'reset' ||
            (t == 'checkbox' || t == 'radio') && !this.checked ||
            (t == 'submit' || t == 'image' || t == 'button') && this.form.clicked != this ||
            this.tagName.toLowerCase() == 'select' && this.selectedIndex == -1)
            return;

        if (t == 'image' && this.form.clicked_x)
            return a.push(
                {name: n+'_x', value: this.form.clicked_x},
                {name: n+'_y', value: this.form.clicked_y}
            );

        if (t == 'select-multiple') {
            $('option:selected', this).each( function() {
                a.push({name: n, value: this.value});
            });
            return;
        }

        a.push({name: n, value: this.value});
    });

    return a;
};
