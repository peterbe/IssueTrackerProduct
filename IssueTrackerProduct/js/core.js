$.id=function(id){return document.getElementById(id)};


function econvert(s) {
   return s.replace(/%7E/g,'~').replace(/%28/g,'(').replace(/%29/g,')').replace(/%20/g,' ').replace(/_dot_| dot |_\._|\(\.\)/gi, '.').replace(/_at_|~at~/gi, '@');
}

function fixEncodedLinks() {
   $("a.aeh", $("#main")).each(function() {
      this.href = econvert(this.href);
      this.innerHTML = econvert(this.innerHTML);
   });
}

function _getNoLines(element) {
   var hardlines = element.value.split('\n');
   var total = hardlines.length;
   for (var i=0, len=hardlines.length; i<len; i++) {
      total += Math.max(Math.round(hardlines[i].length / element.cols), 1) - 1;
   }
   return total;
}


function hideFileAttachments() {
  $('tr.fileattachment').hide();
  $('tr.fileattachment-tip').show();
} 
function showFileAttachments() {
  $('tr.fileattachment-tip').hide();
  $('tr.fileattachment').show();
}

$(function() {
   fixEncodedLinks();
   
   // First, for all the textareas that have lots of lines of text 
   // in them, we want to double their number of rows
   $('textarea.autoexpanding').each(function() {
      if (_getNoLines(this) > parseInt(this.rows))
        this.rows = '' + Math.min(_getNoLines(this) + 2, 50);
   });
            
   // When a user enters new lines, if they have entered more
   // lines than the textarea has rows, then double the textareas rows
   $('textarea.autoexpanding').bind('keyup', function() {
      if (_getNoLines(this) > parseInt(this.rows))
        this.rows = '' + Math.min(_getNoLines(this) + 2, 50);
   });
   
  // Unless we can find a reason not to, hide all the fileattachment input TRs
  if (!($('tr.fileattachment-error').size() || $('tr.fileattachment input[type="checkbox"]').size())) {
     hideFileAttachments();
  } else {
     $('tr.fileattachment a.fileattachment-tip').hide();
  }
  $('input[type="file"]').change(function() {
     if (this.value)
       $('tr.fileattachment a.fileattachment-tip').hide();
     else
       $('tr.fileattachment a.fileattachment-tip:hidden').show();
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



