class Weed {
    constructor(canvas) {
        this.canvas = canvas;
        this.x = 50;
        this.y = canvas.height / 2;
        this.width = 40;
        this.height = 30;
        this.velocity = 0;
        this.gravity = 0.08;
        this.floatOffset = 0;
        this.floatSpeed = 0.05;
    }
    
    update() {
        this.velocity += this.gravity;
        if (this.velocity > 2.0) {
            this.velocity = 2.0;
        }
        
        this.floatOffset += this.floatSpeed;
        let floatEffect = Math.sin(this.floatOffset) * 0.3;
        this.y += this.velocity + floatEffect;
        
        if (this.y - this.height/2 < 0) {
            this.y = this.height/2;
            this.velocity = 0;
        }
        
        if (this.y + this.height/2 > this.canvas.height - 20) {
            this.y = this.canvas.height - 20 - this.height/2;
            this.velocity = 0;
            return true;
        }
        return false;
    }
    
    draw(ctx) {
        ctx.fillStyle = '#44A244';
        ctx.beginPath();
        ctx.ellipse(this.x, this.y, this.width/2, this.height/2, 0, 0, Math.PI * 2);
        ctx.fill();
        
        ctx.strokeStyle = '#2E7D32';
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.moveTo(this.x - this.width/3, this.y);
        ctx.lineTo(this.x + this.width/3, this.y);
        ctx.stroke();
        
        ctx.beginPath();
        ctx.moveTo(this.x, this.y - this.height/3);
        ctx.lineTo(this.x, this.y + this.height/3);
        ctx.stroke();
        
        ctx.fillStyle = '#388E3C';
        ctx.beginPath();
        ctx.moveTo(this.x - this.width/2, this.y);
        ctx.lineTo(this.x - this.width/4, this.y - this.height/4);
        ctx.lineTo(this.x, this.y);
        ctx.fill();
        
        ctx.beginPath();
        ctx.moveTo(this.x + this.width/2, this.y);
        ctx.lineTo(this.x + this.width/4, this.y - this.height/4);
        ctx.lineTo(this.x, this.y);
        ctx.fill();
        
        ctx.beginPath();
        ctx.moveTo(this.x - this.width/3, this.y + this.height/3);
        ctx.lineTo(this.x, this.y + this.height/2);
        ctx.lineTo(this.x + this.width/3, this.y + this.height/3);
        ctx.fill();
    }
    
    jump() {
        this.velocity = -3.8;
        playSound('jump');
    }
    
    reset() {
        this.y = this.canvas.height / 3;
        this.velocity = -1;
        this.floatOffset = 0;
    }
}

// Pipe class
class Pipe {
    constructor(canvas, x) {
        this.canvas = canvas;
        this.x = x;
        this.width = 70;
        this.gap = 240;
        this.passed = false;
        
        this.topHeight = Math.floor(Math.random() * (canvas.height - this.gap - 80)) + 40;
        this.bottomY = this.topHeight + this.gap;
        this.bottomHeight = canvas.height - this.bottomY;
    }
    
    update(speed) {
        this.x -= speed;
    }
    
    isOffScreen() {
        return this.x + this.width < 0;
    }
    
    draw(ctx) {
        // Draw top pipe
        ctx.fillStyle = '#689F38';
        ctx.fillRect(this.x, 0, this.width, this.topHeight);
        
        ctx.fillStyle = '#558B2F';
        ctx.fillRect(this.x - 5, this.topHeight - 20, this.width + 10, 20);
        
        // Draw bottom pipe
        ctx.fillStyle = '#689F38';
        ctx.fillRect(this.x, this.bottomY, this.width, this.bottomHeight);
        
        ctx.fillStyle = '#558B2F';
        ctx.fillRect(this.x - 5, this.bottomY, this.width + 10, 20);
    }
    
    checkCollision(weed) {
        const hitboxReduction = 5;
        const weedLeft = weed.x - weed.width/2 + hitboxReduction;
        const weedRight = weed.x + weed.width/2 - hitboxReduction;
        const weedTop = weed.y - weed.height/2 + hitboxReduction;
        const weedBottom = weed.y + weed.height/2 - hitboxReduction;
        
        if (weedRight > this.x && weedLeft < this.x + this.width && weedTop < this.topHeight) {
            return true;
        }
        
        if (weedRight > this.x && weedLeft < this.x + this.width && weedBottom > this.bottomY) {
            return true;
        }
        
        return false;
    }
}

// Sound functions
const jumpSound = new Audio('https://assets.mixkit.co/active_storage/sfx/3005/3005-preview.mp3');
const scoreSound = new Audio('https://assets.mixkit.co/active_storage/sfx/270/270-preview.mp3');
const gameOverSound = new Audio('https://assets.mixkit.co/active_storage/sfx/3/3-preview.mp3');

let soundEnabled = true;

function playSound(sound) {
    if (!soundEnabled) return;
    
    if (sound === 'jump') {
        jumpSound.currentTime = 0;
        jumpSound.play().catch(e => console.log('Sound play error:', e));
    } else if (sound === 'score') {
        scoreSound.currentTime = 0;
        scoreSound.play().catch(e => console.log('Sound play error:', e));
    } else if (sound === 'death') {
        gameOverSound.currentTime = 0;
        gameOverSound.play().catch(e => console.log('Sound play error:', e));
    }
}

// Game variables
const canvas = document.getElementById('game-canvas');
const ctx = canvas.getContext('2d');
const scoreDisplay = document.querySelector('.score');
const startScreen = document.querySelector('.start-screen');
const gameOverScreen = document.querySelector('.game-over');
const finalScoreDisplay = document.getElementById('final-score');
const startButton = document.getElementById('start-button');
const restartButton = document.getElementById('restart-button');
const submitScoreButton = document.getElementById('submit-score');
        
let gameActive = false;
let score = 0;
let highScore = localStorage.getItem('highScore') || 0;
let gravity = 0.08; 
let pipes = [];
let pipeWidth = 70;
let pipeGap = 240;
let pipeSpeed = 2.5;     // INCREASED TO 2.5
let minPipeHeight = 40;
let nextPipe = 50;       // REDUCED TO 50
let pipeInterval = 50;   // REDUCED TO 50

// Weed character
const weed = new Weed(canvas);

// Get game session from URL parameters
function getUrlParameter(name) {
    name = name.replace(/[\[]/, '\\[').replace(/[\]]/, '\\]');
    var regex = new RegExp('[\\?&]' + name + '=([^&#]*)');
    var results = regex.exec(location.search);
    return results === null ? '' : decodeURIComponent(results[1].replace(/\+/g, ' '));
}

const gameSession = getUrlParameter('session');

// Draw background 
function drawBackground() {
    // Sky gradient
    const skyGradient = ctx.createLinearGradient(0, 0, 0, canvas.height);
    skyGradient.addColorStop(0, '#87CEEB');
    skyGradient.addColorStop(1, '#E0F7FF');
    ctx.fillStyle = skyGradient;
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    
    // Ground
    ctx.fillStyle = '#8B4513';
    ctx.fillRect(0, canvas.height - 20, canvas.width, 20);
    
    // Grass
    ctx.fillStyle = '#7CFC00';
    ctx.fillRect(0, canvas.height - 25, canvas.width, 5);
}

// Create pipe
function createPipe() {
    return new Pipe(canvas, canvas.width);
}

// Game loop
function gameLoop() {
    if (!gameActive) return;
    
    // Clear canvas
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    
    // Draw background
    drawBackground();
    
    // Create new pipes
    nextPipe--;
    if (nextPipe <= 0) {
        pipes.push(createPipe());
        nextPipe = pipeInterval;
    }
    
    // Draw and update pipes
    for (let i = 0; i < pipes.length; i++) {
        const pipe = pipes[i];
        pipe.update(pipeSpeed);
        pipe.draw(ctx);
        
        // Score when passing pipe
        if (!pipe.passed && pipe.x + pipe.width < weed.x) {
            score++;
            scoreDisplay.textContent = score;
            pipe.passed = true;
            playSound('score');
        }
        
        // Check collision
        if (pipe.checkCollision(weed)) {
            gameOver();
            return;
        }
        
        // Remove offscreen pipes
        if (pipe.isOffScreen()) {
            pipes.splice(i, 1);
            i--;
        }
    }
    
    // Update weed character
    const hitGround = weed.update();
    if (hitGround) {
        gameOver();
        return;
    }
    
    // Draw weed
    weed.draw(ctx);
    
    // Continue game loop
    requestAnimationFrame(gameLoop);
}

// Start game
function startGame() {
    gameActive = true;
    score = 0;
    pipes = [];
    nextPipe = 50; // Start with first pipe sooner
    
    weed.reset();
    scoreDisplay.textContent = score;
    startScreen.style.display = 'none';
    gameOverScreen.style.display = 'none';
    
    gameLoop();
}

// Game over
function gameOver() {
    gameActive = false;
    playSound('death');
    
    // Update high score
    if (score > highScore) {
        highScore = score;
        localStorage.setItem('highScore', highScore);
    }
    
    gameOverScreen.style.display = 'flex';
    finalScoreDisplay.textContent = score;
    
    // Show high score if element exists
    const highScoreElement = document.getElementById('high-score');
    if (highScoreElement) {
        highScoreElement.textContent = highScore;
    }
}

// Save score to Telegram
function saveScore() {
    const data = {
        session: gameSession,
        score: score
    };
    
    try {
        // Telegram WebApp API
        if (window.Telegram && window.Telegram.WebApp) {
            window.Telegram.WebApp.sendData(JSON.stringify(data));
            alert("Skorunuz kaydedildi!");
        } else {
            // Fallback to URL redirect
            window.location.href = `https://t.me/Yesiltobacco_bot?start=save_score_${gameSession}_${score}`;
        }
    } catch (e) {
        console.error("Skor kaydedilirken hata:", e);
        alert("Skor kaydedilemedi, lütfen tekrar deneyin.");
    }
}

// Event listeners
canvas.addEventListener('click', function() {
    if (gameActive) {
        weed.jump();
    }
});

canvas.addEventListener('touchstart', function(e) {
    e.preventDefault();
    if (gameActive) {
        weed.jump();
    }
});

// Keyboard controls
document.addEventListener('keydown', function(e) {
    if ((e.code === 'Space' || e.code === 'ArrowUp') && gameActive) {
        weed.jump();
        e.preventDefault();
    }
});

// Button events
startButton.addEventListener('click', startGame);
restartButton.addEventListener('click', startGame);
submitScoreButton.addEventListener('click', saveScore);

// Initial screen
drawBackground();
weed.draw(ctx);