class Weed {
    constructor(canvas) {
        this.canvas = canvas;
        this.x = 50;
        this.y = canvas.height / 2;
        this.width = 40;
        this.height = 30;
        this.velocity = 0;
        this.gravity = 0.25;
        this.floatOffset = 0;
        this.floatSpeed = 0.05;
    }
    
    update() {
        // Hareket ve fizik burada
    }
    
    draw(ctx) {
        // Çizim işlemleri burada
    }
    
    jump() {
        this.velocity = -5.5;
        // Ses çal
        game.sound.play('jump');
    }
    
    reset() {
        // Karakter pozisyonunu sıfırla
    }
}