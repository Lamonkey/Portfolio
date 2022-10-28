function loadJson(selector) {
  return JSON.parse($(selector).attr('data-json'))
}
let jsonData;
//load all project
$(document).ready(function () {
  jsonData = loadJson('#jsonData')
  //project wrapper 
  let project_wrapper = document.createElement("div")
  project_wrapper.className="projects"
  //Add project_wrapper to this tag
  const project_list = $('#projectlist');

element.classList.add('animate__animated', 'animate__bounceOutLeft');
  jsonData.forEach(project => {
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
    project_wrapper.classList.add('animate__animated', 'animate__backInLeft')
    project_list.append(projecthtml);

  });

//filter project
$('.nav-link').click(function(){
  let tag = $(this).text().toLowerCase()
  $('.projects').remove()
  jsonData.forEach(project=>{
    if( project.type.toLowerCase() == tag || 'all' == tag){
      var projecthtml = '<div class = "projects">'+
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
      '</li>'+
      '</div>'
    $("#projectlist").append(projecthtml).hide().show('slow')
    }
  })
  // alert(`clicked ${$(this).text()}`)
})
})