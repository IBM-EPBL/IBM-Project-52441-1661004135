const image = document.getElementById('myImage');


function readURL(input) 
{
    //document.getElementById("bannerImg").style.display = "block";

    if (input.files && input.files[0]) {
        var reader = new FileReader();

        reader.onload = function (e) {
            image.src =  e.target.result;
        }

        reader.readAsDataURL(input.files[0]);
    }
}
