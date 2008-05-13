function changeAddSelect(select) {
  if (select.options[select.selectedIndex].value=='++other++') {
     document.getElementById('other').style['display']='';
  } else if (select.options[select.selectedIndex].value) {
     select.form.submit();
  }
}

function toggleOptionsInput2Expression() {
  $('.options-list').hide();
  $('.options-expression').show();  
}

function toggleOptionsInput2List() {
  $('input', $('.options-expression')).val('');
  $('.options-expression').hide();
  $('.options-list').show();
}

function toggleTextareaSize(click, textarea_id) {
   var txta = $('#' + textarea_id);
   if ($(click).text()=='+') {
      txta.attr('cols','140').attr('rows','30');
      $(click).text('-').attr('title', 'Make it smaller');
   } else {
      txta.attr('cols','60').attr('rows','6');
      $(click).text('+').attr('title', 'Make it larger');
   }
}

function toggleInputSize(click, input_id) {
   var inp = $('#' + input_id);
   if ($(click).text()=='+') {
      inp.attr('size','150');
      $(click).text('-').attr('title', 'Make it smaller');
   } else {
      inp.attr('size','50');
      $(click).text('+').attr('title', 'Make it larger');
   }
}

$(function() {
  // hide options-expression if empty
  if ($('.options-expression').size()) {
    if (!$('input', $('dd.options-expression')).val()) {
      $('.options-expression').hide();
    } else {
      $('.options-list').hide();
    }
  }
  
  // Add an expander to all textareas
  var count = 0;
  $('textarea').each(function() {
     var textarea_id = $(this).attr('id');
     if (!textarea_id) {
        textarea_id = 'textarea-' + count;
        $(this).attr('id', textarea_id)
     }
     $(this).after($('<a></a>').attr('href','#').attr('title','Make it larger').click(function() {
        toggleTextareaSize(this, textarea_id);
        return false;
     }).text('+'));
     
     count++;
  });
   
  
  $('input', $('dl.attributes')).each(function() {
     var input_id = $(this).attr('id');
     if (!input_id) {
        input_id = 'input-' + count;
        $(this).attr('id', input_id)
     }
     $(this).after($('<a></a>').attr('href','#').attr('title','Make it larger').click(function() {
        toggleInputSize(this, input_id);
        return false;
     }).text('+'));
     count++;
  });   
  
});
