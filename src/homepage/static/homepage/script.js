function loadJson(selector) {
  return JSON.parse($(selector).attr('data-json'))
}
let jsonData;
//load all project
$(document).ready(function () {
  jsonData = loadJson('#jsonData')

  // element.classList.add('animate__animated', 'animate__bounceOutLeft');
  jsonData.forEach(project => {
    //project wrapper 
    let project_wrapper = document.createElement("div")
    project_wrapper.className = "projects"
    //getting type
    let types = project.type
    types.push("all")
    project_wrapper.innerHTML =
      '<li class="list-group-item">' +
      '<div class="category">' +
      `<p hidden> ${project.type} </p>` +
      '</div>' +
      '<div class="row">' +
      ' <div class=" col-md-7 col-sm-7 col-12">' +
      `<img src="${project.image}" class="image-responsive" alt="{{project.title}}"> </div>` +
      ' <div class=" col-md-5 col-sm-5 col-12">' +
      '<div class="row">' +
      '<div class="col-11 col-md-11 col-sm-11">' +
      `<p class="title"> ${project.title}</p>` +
      `<p class="description"> ${project.description} </p>` +
      '</div>' +
      ' <div class="col-12 col-md-12 col-sm-12 offset-3 offset-sm-0 offset-md-0">' +
      `<a class="btn btn-success" href=${project.link} target=_blank` +
      '  role="button">Click to' +
      ' Checkout!</a>' +
      ' </div>' +
      ' </div>' +
      ' </div>' +
      '</div>' +
      '</li>';
    //add animation
    project_wrapper.classList.add('animate__animated', 'animate__backInLeft')
    //add type list as attribute
    project_wrapper.setAttribute("types", types)
    $('#projectlist').append(project_wrapper);
  });
  //add event lisener to each project

  //filter project
  $('.nav-link').click(function () {
    //filter project
    let selected_type = $(this).attr("value")
    let selected_project = $('.projects').filter(function () {
      let types = $(this).attr("types").split(",")
      return types.includes(selected_type)
    });
    let unselected_project = $('.projects').filter(function () {
      let types = $(this).attr("types").split(",")
      return !types.includes(selected_type)
    });
    //slide in selected project
    selected_project.each(function (index, element) {
      if ($(this).hasClass("animate__backOutLeft")) {
        $(this).show()
        $(this).addClass("animate__backInLeft").removeClass("animate__backOutLeft")
        // $(this).on("animationend", () => {
        //   // $(this).attr("hidden",false)
        //   $(this).show()
        // });
      }
    })
    //slide out unselected project
    unselected_project.each(function (index, element) {
      if ($(this).hasClass("animate__backInLeft")) {
        $(this).addClass("animate__backOutLeft").removeClass("animate__backInLeft")
        $(this).on("animationend", () => {
          // $(this).attr("hidden",true)
          if ($(this).hasClass("animate__backOutLeft")){
            $(this).hide()
          }
        });
      }
    })
    // $('.projects').on('animationend', () => {
    //   //show when slide in 
    //   if ($(this).hasClass("animate__backInLeft")) {
    //     $(this).attr("hidden", false);
    //     alert("unhide this project")
    //   }
    //   //hide when slide out
    //   else if ($(this).hasClass("animate__backInLeft")) {
    //     $(this).attr("hidden", true);
    //     alert("hide this project")
    //   }
    // });
  })
})