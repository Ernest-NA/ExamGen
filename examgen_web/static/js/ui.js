(function(){
  var toasts=document.querySelectorAll('.toast');
  toasts.forEach(function(t){
    var delay=parseInt(t.getAttribute('data-timeout')||'4000',10);
    setTimeout(function(){t.remove();},delay);
  });
  document.querySelectorAll('.skip-link').forEach(function(sk){
    sk.addEventListener('click',function(){
      var id=this.getAttribute('href').slice(1);
      var el=document.getElementById(id);
      if(el){el.setAttribute('tabindex','-1');el.focus();}
    });
  });
})();
