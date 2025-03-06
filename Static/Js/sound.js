const jumpSound = new Audio('https://assets.mixkit.co/active_storage/sfx/3005/3005-preview.mp3');
const scoreSound = new Audio('https://assets.mixkit.co/active_storage/sfx/270/270-preview.mp3');
const gameOverSound = new Audio('https://assets.mixkit.co/active_storage/sfx/3/3-preview.mp3');

// Sesi açıp kapama değişkeni (isteğe bağlı)
let soundEnabled = true;

// HTML'e ses açma kapama butonu ekleyin (start-screen ve game-over içine)
// <button id="toggle-sound">🔊</button>

// Ses açma/kapama butonu işleyicisi ekleyin
/*
document.getElementById('toggle-sound').addEventListener('click', function() {
    soundEnabled = !soundEnabled;
    this.textContent = soundEnabled ? '🔊' : '🔇';
});
*/

// playSound fonksiyonunu güncelleyin
function playSound(sound) {
    if (!soundEnabled) return; // Ses kapalıysa çalma
    
    if (sound === 'jump') {
        jumpSound.currentTime = 0;
        jumpSound.play();
    } else if (sound === 'score') {
        scoreSound.currentTime = 0;
        scoreSound.play();
    } else if (sound === 'death') {
        gameOverSound.currentTime = 0;
        gameOverSound.play();
    }
}