class Game {
    constructor() {
        this.canvas = document.getElementById('game-canvas');
        this.ctx = this.canvas.getContext('2d');
        this.score = 0;
        this.gameActive = false;
        this.pipes = [];
        this.pipeSpeed = 3.0;
        this.pipeInterval = 100;
        this.nextPipe = 100;
        
        // Karakter ve arkaplan modüllerini oluştur
        this.weed = new Weed(this.canvas);
        this.background = new Background(this.canvas);
        this.sound = new Sound();
        
        // Olay dinleyicileri
        this.setupEventListeners();
    }
    
    setupEventListeners() {
        // Tıklama, dokunma ve buton olayları burada
    }
    
    start() {
        this.gameActive = true;
        this.score = 0;
        this.pipes = [];
        this.nextPipe = 100;
        this.weed.reset();
        this.gameLoop();
    }
    
    gameLoop() {
        if (!this.gameActive) return;
        
        // Ekranı temizle
        this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
        
        // Arkaplanı çiz
        this.background.draw(this.ctx);
        
        // Boruları oluştur ve yönet
        this.managePipes();
        
        // Karakteri güncelle ve çiz
        this.weed.update();
        this.weed.draw(this.ctx);
        
        // Sonraki kareyi iste
        requestAnimationFrame(() => this.gameLoop());
    }
    
    managePipes() {
        // Boru oluşturma, güncelleme ve çarpışma kontrolü
    }
    
    gameOver() {
        this.gameActive = false;
        this.sound.play('death');
        // Oyun sonu işlemleri
    }
}
