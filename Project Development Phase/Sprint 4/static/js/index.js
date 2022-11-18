
  const signUpButton = document.getElementById('signUp');
  const signInButton = document.getElementById('signIn');
  const container = document.getElementById('container');

  const switchone = document.getElementById('c1');
  const switchtwo = document.getElementById("c2");
  const switchthree = document.getElementById('c3');
  const switchfour = document.getElementById('c4');

  const Fswitchone = document.getElementById('l1');
  const Fswitchtwo = document.getElementById("l2");
  const Fswitchthree = document.getElementById('l3');
  const Fswitchfour = document.getElementById('l4');

  const space = document.getElementById('infos');

  var pre_state = 0;
  var stateone = 0;
  var statetwo = 0;
  var statethree = 0;

  signUpButton.addEventListener('click', () => {
  container.classList.add("right-panel-active");
});

  signInButton.addEventListener('click', () => {
  container.classList.remove("right-panel-active");
});

switchone.addEventListener('click', remover);
switchtwo.addEventListener('click', signin);
switchthree.addEventListener('click', Signup)
switchfour.addEventListener('click', about);

Fswitchone.addEventListener('click', remover);
Fswitchtwo.addEventListener('click', signin);
Fswitchthree.addEventListener('click', Signup)
Fswitchfour.addEventListener('click', about);


function remover() {

  if(pre_state == 1){
    pre_state = 0;
    space.classList.remove("spaceimp");
    document.getElementById("abouts").style.display = "none";
    document.getElementById("logins").style.display = "none";
    document.getElementById("l1").style.display = "flex";
    document.getElementById("l2").style.display = "flex";
    document.getElementById("l3").style.display = "flex";
    document.getElementById("l4").style.display = "flex";
}
}

function div_adder () {
  space.classList.add("spaceimp");
  document.getElementById("abouts").style.display = "none";
  document.getElementById("logins").style.display = "block";
  document.getElementById("l1").style.display = "none";
  document.getElementById("l2").style.display = "none";
  document.getElementById("l3").style.display = "none";
  document.getElementById("l4").style.display = "none";
}

function about_adder () {
  //space.classList.add("spaceimp");
 // remover();
  document.getElementById("abouts").style.display = "block";
  document.getElementById("l1").style.display = "none";
  document.getElementById("l2").style.display = "none";
  document.getElementById("l3").style.display = "none";
  document.getElementById("l4").style.display = "none";
}


function signin() {

  if(pre_state == 0) {
    pre_state = 1;
    stateone = 1;
    statetwo = 0;
    statethree = 0;
    container.classList.remove("right-panel-active");
    div_adder();
  }else {
    if(stateone == 0) {
      pre_state = 1;
      stateone = 1;
      statetwo = 0;
      statethree = 0;
      container.classList.remove("right-panel-active");
      div_adder();
    }else {
      remover();
    }
  }

}

function Signup() {
  
  if(pre_state == 0) {
    pre_state = 1;
    stateone = 0;
    statetwo = 1;
    statethree = 0;
    container.classList.add("right-panel-active");
    div_adder();
  }else {
    if(statetwo == 0) {
      pre_state = 1;
      stateone = 0;
      statetwo = 1;
      statethree = 0;
      container.classList.add("right-panel-active");
      div_adder();
    }else {
      remover();
    }
  }
}

function about() {
  if(pre_state == 0){
    pre_state = 1;
    stateone = 0;
    statetwo = 0;
    statethree = 3;
    about_adder();
  }else{
    if(statethree == 0){
      remover();
      pre_state = 1;
      stateone = 0;
      statetwo = 0;
      statethree = 3;
      about_adder();
    }else{
      remover();
    }
  }
  
}

function unvisible(x) {
    if(pre_state == 0) {
      document.getElementById("l1").style.display = "none";
      document.getElementById("l2").style.display = "none";
      document.getElementById("l3").style.display = "none";
      document.getElementById("l4").style.display = "none";
    }
    
  }

  function visible(x){
    if(pre_state == 0) {
      document.getElementById("abouts").style.display = "block";
      //space.classList.add("spaceimp");
      container.classList.add("right-panel-active");
      document.getElementById("l1").style.display = "none";
      document.getElementById("l2").style.display = "none";
      document.getElementById("l3").style.display = "none";
      document.getElementById("l4").style.display = "none";
    }
  }

  function unsignin(x) {
    if(pre_state == 0){
      container.classList.remove("right-panel-active");
      space.classList.remove("spaceimp");
      document.getElementById("logins").style.display = "none";
      document.getElementById("abouts").style.display = "none";
      document.getElementById("l1").style.display = "flex";
      document.getElementById("l2").style.display = "flex";
      document.getElementById("l3").style.display = "flex";
      document.getElementById("l4").style.display = "flex";
    }
    
  }


  function signinOne(x){
    if(pre_state == 0) {
      container.classList.remove("right-panel-active");
      space.classList.add("spaceimp");
      document.getElementById("logins").style.display = "block";
      document.getElementById("l1").style.display = "none";
      document.getElementById("l2").style.display = "none";
      document.getElementById("l3").style.display = "none";
      document.getElementById("l4").style.display = "none";
    }
  }

  function signinTwo(x){
    if(pre_state == 0) {
      document.getElementById("logins").style.display = "block";
      space.classList.add("spaceimp");
      container.classList.add("right-panel-active");
      document.getElementById("l1").style.display = "none";
      document.getElementById("l2").style.display = "none";
      document.getElementById("l3").style.display = "none";
      document.getElementById("l4").style.display = "none";
    }

  function setcon(x) {
    if(pre_state == 0) {
      document.getElementById("abouts").style.display = "block";
        //space.classList.add("spaceimp");
      container.classList.add("right-panel-active");
      document.getElementById("l1").style.display = "none";
      document.getElementById("l2").style.display = "none";
      document.getElementById("l3").style.display = "none";
      document.getElementById("l4").style.display = "none";
      }
  }
 
}
