$(window).scroll(function(){
      if ($(this).scrollTop() > -10) {
          $('.nava').addClass('fixed');
      } else {
          $('.nava').removeClass('fixed');
      }
});

var animateButton = function(e) {

  e.preventDefault;
  //reset animation
  e.target.classList.remove('animate');
  
  e.target.classList.add('animate');
  setTimeout(function(){
    e.target.classList.remove('animate');
  },700);
};

var bubblyButtons = document.getElementsByClassName("bubbly-button");

for (var i = 0; i < bubblyButtons.length; i++) {
  bubblyButtons[i].addEventListener('click', animateButton, false);
}


document.querySelector('.like-button').addEventListener('click', (e) => {
  e.currentTarget.classList.toggle('liked');
});