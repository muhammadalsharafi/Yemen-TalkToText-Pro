const mouseBall = document.querySelector('.mouse-ball');
let mouseX = 0;
let mouseY = 0;
let ballX = 0;
let ballY = 0;
const speed = 0.02; 



document.addEventListener('mousemove', (e) => {
  mouseX = e.clientX - mouseBall.offsetWidth / 2;
  mouseY = e.clientY - mouseBall.offsetHeight / 2;
});

function animate()
{
  ballX += (mouseX - ballX) * speed;
  ballY += (mouseY - ballY) * speed;
  mouseBall.style.transform = `translate(${ballX}px, ${ballY}px)`;
  requestAnimationFrame(animate);
}
animate();


//---------------------------------------------------------------------(signup)

async function signupUser() {
  const fname = document.getElementById("fname").value;
  const lname = document.getElementById("lname").value;
  const email = document.getElementById("email").value;
  const password = document.getElementById("password").value;
  const password_again = document.getElementById("password_again").value;


  if (!fname || !lname || !email || !password || !password_again) {
    alert("fill all the fields");
    return;
  }
if (password == password_again) {
          try {
            const response = await fetch("/signup", {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ fullname: fname + " " + lname, email, password })
            });

            const result = await response.json();

            if (result.success) {
              window.location.href = "/login";
            } else {
              alert(result.error);
            }

          } catch (error) {
            alert("problem occurred");
          }
        }
        else
        {
          alert("passwords do not match");
          return;
        }
}
//--------------------------------------------(login)


async function loginUser() {
  const email = document.getElementById("email").value;
  const password = document.getElementById("password").value;

  if (!email || !password) {
    alert("fill all the fields");
    return;
  }

  try {
    const response = await fetch("/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password })
    });

    const result = await response.json();

    if (result.success) {
      window.location.href = "/dashboard"; 
    } else {
      alert(result.error);
    }
  } catch (error) {
    alert("problem occurred");
  }
}


















const signupButton = document.getElementById("submit-btn-signup");
if (signupButton) {
    signupButton.addEventListener("click", signupUser);
}

document.getElementById("submit-btn-login")?.addEventListener("click", loginUser);