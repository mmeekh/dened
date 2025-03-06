class Sound {
    constructor() {
        // Load sounds
        this.jumpSound = new Audio('https://assets.mixkit.co/active_storage/sfx/3005/3005-preview.mp3');
        this.scoreSound = new Audio('https://assets.mixkit.co/active_storage/sfx/270/270-preview.mp3');
        this.gameOverSound = new Audio('https://assets.mixkit.co/active_storage/sfx/3/3-preview.mp3');
        
        // Enable sound by default
        this.soundEnabled = true;
        
        // Pre-load sounds to reduce latency
        this.jumpSound.load();
        this.scoreSound.load();
        this.gameOverSound.load();
    }
    
    play(sound) {
        if (!this.soundEnabled) return;
        
        if (sound === 'jump') {
            this.jumpSound.currentTime = 0;
            this.jumpSound.play().catch(e => console.log('Sound play error:', e));
        } else if (sound === 'score') {
            this.scoreSound.currentTime = 0;
            this.scoreSound.play().catch(e => console.log('Sound play error:', e));
        } else if (sound === 'death') {
            this.gameOverSound.currentTime = 0;
            this.gameOverSound.play().catch(e => console.log('Sound play error:', e));
        }
    }
    
    toggle() {
        this.soundEnabled = !this.soundEnabled;
        return this.soundEnabled;
    }
}