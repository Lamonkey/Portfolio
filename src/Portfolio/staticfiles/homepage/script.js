var darkMode = true;

document.addEventListener("click", function (event) {
  //filter button
  if (event.target.classList.contains("nav-link")) {
    event.preventDefault(); // prevent the default behavior
    event.stopPropagation(); // stop the event from propagating
    let category = event.target.attributes.value.value;
    if (category == "all") {
      let all_element = document.getElementsByClassName(
        "projects-container-content"
      );
      for (let i = 0; i < all_element.length; i++) {
        all_element[i].style.display = "block";
      }
    } else {
      //show selected
      let elements = document.querySelectorAll(
        `.projects-container-content.${category}`
      );
      for (let i = 0; i < elements.length; i++) {
        elements[i].style.display = "block";
      }
      //hide unselected
      elements = document.querySelectorAll(
        `.projects-container-content:not(.${category})`
      );
      for (let i = 0; i < elements.length; i++) {
        elements[i].style.display = "none";
      }
    }
  }
  //dark mode button
  else if (event.target.classList.contains("toggler-slider-circle") || 
  event.target.classList.contains("toggler-slider")) {
    darkMode = !darkMode

    if (darkMode){
      //add class to body
      document.body.classList.add("dark_mode")
      //add class to navbar
      document.getElementsByTagName("nav")[0].classList.add('bg-dark')
      //add attribute to navbar
      document.getElementsByTagName("nav")[0].setAttribute('data-bs-theme','dark')
    }
    else{
      //remove class from body
      document.body.classList.remove('dark_mode')
      //remove class from navbar
      document.getElementsByTagName("nav")[0].classList.remove('bg-dark')
      document.getElementsByTagName("nav")[0].setAttribute('data-bs-theme','light')
    }




    // let state = document.getElementById("mode-value").attributes.value.value;
    // if (state == "light") {
    //   document.getElementById("mode-value").attributes.value.value = "dark";
     
    //   document.body.classList.remove("light_mode");
    //   document.body.classList.add("dark_mode");
    //   let navbar = document.getElementsByTagName("nav")[0];
    //   navbar.classList.remove("bg-body-tertiary");
    //   navbar.classList.add("bg-dark");
    //   navbar.setAttribute("data-bs-theme","dark" );
    // } else {
    
     
    //   document.body.classList.remove("dark_mode");
    //   document.body.classList.add("light_mode");
    //   let navbar = document.getElementsByTagName("nav")[0];
    //   navbar.classList.remove("bg-dark");
    //   navbar.attributes.removeNamedItem("data-bs-theme");
    //   navbar.classList.add("bg-body-tertiary");
    // }
  }
});
//
