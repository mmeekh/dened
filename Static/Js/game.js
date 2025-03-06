class Game {
    constructor() {
        // Get canvas and context
        this.canvas = document.getElementById('game-canvas');
        this.ctx = this.canvas.getContext('2d');
        
        // Game state variables
        this.score = 0;
        this.gameActive = false;
        this.pipes = [];
        this.pipeSpeed = 2.5;  // Increased from 1.8 to 2.5 (roughly 1.4x faster)
        this.pipeInterval = 70;  // Kept the same interval
        this.nextPipe = 70;  // Adjusted to match initial interval
        this.gameStartTime = 0;
        this.elapsedFrames = 0;
        this.highScore = localStorage.getItem('highScore') || 0;
        
        // Create game objects
        this.weed = new Weed(this.canvas);
        this.background = new Background(this.canvas);
        this.sound = new Sound();
        
        // Setup event listeners
        this.setupEventListeners();
    }
    
    setupEventListeners() {
        // Mouse click / touch event
        this.canvas.addEventListener('click', () => {
            if (this.gameActive) {
                this.weed.jump();
            }
        });
        
        // Touch events
        this.canvas.addEventListener('touchstart', (e) => {
            e.preventDefault();
            if (this.gameActive) {
                this.weed.jump();
            }
        });
        
        // Keyboard event for spacebar and arrow up
        document.addEventListener('keydown', (e) => {
            if ((e.code === 'Space' || e.code === 'ArrowUp') && this.gameActive) {
                this.weed.jump();
                e.preventDefault(); // Prevent page scrolling
            }
        });
        
        // Start button
        document.getElementById('start-button').addEventListener('click', () => {
            this.start();
        });
        
        // Restart button
        document.getElementById('restart-button').addEventListener('click', () => {
            this.start();
        });
        
        // Submit score button
        document.getElementById('submit-score').addEventListener('click', () => {
            this.submitScore();
        });
        
        // Optional: Sound toggle button
        // const toggleSoundButton = document.getElementById('toggle-sound');
        // if (toggleSoundButton) {
        //     toggleSoundButton.addEventListener('click', () => {
        //         const soundEnabled = this.sound.toggle();
        //         toggleSoundButton.textContent = soundEnabled ? '🔊' : '🔇';
        //     });
        // }
    }
    
    start() {
        // Reset game state
        this.gameActive = true;
        this.score = 0;
        this.pipes = [];
        this.nextPipe = 100;
        this.gameStartTime = Date.now();
        this.elapsedFrames = 0;
        
        // Reset weed position
        this.weed.reset();
        
        // Hide start and game over screens
        document.querySelector('.start-screen').style.display = 'none';
        document.querySelector('.game-over').style.display = 'none';
        
        // Reset score display
        document.querySelector('.score').textContent = this.score;
        
        // Start game loop
        this.gameLoop();
    }
    
    gameLoop() {
        if (!this.gameActive) return;
        
        // Increment frame counter
        this.elapsedFrames++;
        
        // Clear canvas
        this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
        
        // Draw background
        this.background.draw(this.ctx);
        
        // Manage pipes
        this.managePipes();
        
        // Update weed
        const hitGround = this.weed.update();
        if (hitGround) {
            this.gameOver();
            return;
        }
        
        // Draw weed
        this.weed.draw(this.ctx);
        
        // Request next frame
        requestAnimationFrame(() => this.gameLoop());
    }
    
    managePipes() {
        // Create new pipes
        this.nextPipe--;
        if (this.nextPipe <= 0) {
            this.pipes.push(new Pipe(this.canvas, this.canvas.width));
            
            // Make pipes come slightly faster as the game progresses
            // but not too fast
            this.pipeInterval = Math.max(60, 70 - Math.floor(this.elapsedFrames / 800));
            this.nextPipe = this.pipeInterval;
        }
        
        // Update and draw pipes
        for (let i = 0; i < this.pipes.length; i++) {
            const pipe = this.pipes[i];
            
            // Update pipe position
            pipe.update(this.pipeSpeed);
            
            // Check for scoring - when weed passes a pipe
            if (!pipe.passed && pipe.x + pipe.width < this.weed.x) {
                this.score++;
                pipe.passed = true;
                document.querySelector('.score').textContent = this.score;
                this.sound.play('score');
            }
            
            // Check for collision
            if (pipe.checkCollision(this.weed)) {
                this.gameOver();
                return;
            }
            
            // Draw pipe
            pipe.draw(this.ctx);
            
            // Remove pipes that have gone off screen
            if (pipe.isOffScreen()) {
                this.pipes.splice(i, 1);
                i--;
            }
        }
    }
    
    gameOver() {
        this.gameActive = false;
        this.sound.play('death');
        
        // Update high score if needed
        if (this.score > this.highScore) {
            this.highScore = this.score;
            localStorage.setItem('highScore', this.highScore);
        }
        
        // Show game over screen
        const gameOverScreen = document.querySelector('.game-over');
        gameOverScreen.style.display = 'flex';
        
        // Update final score
        document.getElementById('final-score').textContent = this.score;
        
        // Show high score if element exists
        const highScoreElement = document.getElementById('high-score');
        if (highScoreElement) {
            highScoreElement.textContent = this.highScore;
        }
    }
    
    submitScore() {
        // Get game session from URL parameters
        const urlParams = new URLSearchParams(window.location.search);
        const gameSession = urlParams.get('session');
        
        if (gameSession) {
            // For Telegram WebApp
            if (window.Telegram && window.Telegram.WebApp) {
                window.Telegram.WebApp.sendData(JSON.stringify({
                    session: gameSession,
                    score: this.score
                }));
            } else {
                // Fallback to URL redirect if WebApp API not available
                window.location.href = `https://t.me/Yesiltobacco_bot?start=save_score_${gameSession}_${this.score}`;
            }
        } else {
            alert('No game session found! Your score will not be saved.');
        }
    }
}

// Create game instance when page loads
let game;
window.onload = function() {
    game = new Game();
};