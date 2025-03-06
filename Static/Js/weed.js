// Karakter görseli
const characterImage = new Image();
characterImage.src = 'data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAxMDAgMTAwIj48ZWxsaXBzZSBjeD0iNTAiIGN5PSI1MCIgcng9IjQwIiByeT0iMzAiIGZpbGw9IiM0NEEyNDQiIHN0cm9rZT0iIzJFN0QzMiIgc3Ryb2tlLXdpZHRoPSIyIiAvPjxwYXRoIGQ9Ik0zMCA1MCBMNzAgNTAiIHN0cm9rZT0iIzJFN0QzMiIgc3Ryb2tlLXdpZHRoPSIzIiAvPjxwYXRoIGQ9Ik01MCAzMCBMNTAgNzAiIHN0cm9rZT0iIzJFN0QzMiIgc3Ryb2tlLXdpZHRoPSIzIiAvPjxwYXRoIGQ9Ik0xMCA1MCBMMzAgMzUgTDUwIDUwIiBmaWxsPSIjMzg4RTNDIiAvPjxwYXRoIGQ9Ik05MCA1MCBMNzAgMzUgTDUwIDUwIiBmaWxsPSIjMzg4RTNDIiAvPjxwYXRoIGQ9Ik0zMCA2NSBMNTAgODAgTDcwIDY1IiBmaWxsPSIjMzg4RTNDIiAvPjxlbGxpcHNlIGN4PSIzNSIgY3k9IjM1IiByeD0iMTAiIHJ5PSI4IiBmaWxsPSJyZ2JhKDI1NSwyNTUsMjU1LDAuMikiIC8+PGNpcmNsZSBjeD0iNDAiIGN5PSI0NSIgcj0iNSIgZmlsbD0id2hpdGUiIC8+PGNpcmNsZSBjeD0iNjAiIGN5PSI0NSIgcj0iNSIgZmlsbD0id2hpdGUiIC8+PGNpcmNsZSBjeD0iNDAiIGN5PSI0NSIgcj0iMiIgZmlsbD0iYmxhY2siIC8+PGNpcmNsZSBjeD0iNjAiIGN5PSI0NSIgcj0iMiIgZmlsbD0iYmxhY2siIC8+PHBhdGggZD0iTTQwIDYwIFE1MCA3MCA2MCA2MCIgZmlsbD0ibm9uZSIgc3Ryb2tlPSJibGFjayIgc3Ryb2tlLXdpZHRoPSIyIiAvPjwvc3ZnPg==';

class Weed {
    constructor(canvas) {
        this.canvas = canvas;
        this.x = 50;
        this.y = canvas.height / 2;
        this.width = 40;  // Görselin genişliği
        this.height = 40; // Görselin yüksekliği
        this.velocity = 0;
        this.gravity = 0.08;
        this.floatOffset = 0;
        this.floatSpeed = 0.05;
        // Görselin yüklenmesi için hazırlık
        this.image = characterImage;
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
        ctx.save(); // Mevcut çizim durumunu kaydet
        
        // Karakterin hareketi için açı hesaplama
        let angle = 0;
        if (this.velocity < 0) {
            // Yukarı doğru hareket ederken hafif yukarı bak
            angle = -Math.PI/15; // Yaklaşık -12 derece
        } else if (this.velocity > 1) {
            angle = Math.PI/15; // Yaklaşık 12 derece
        }
        
        ctx.translate(this.x, this.y);
        ctx.rotate(angle);
        
        ctx.drawImage(
            this.image, 
            -this.width/2, 
            -this.height/2, 
            this.width, 
            this.height
        );
        
        ctx.restore(); // Çizim durumunu geri yükle
    }
    
    jump() {
        this.velocity = -3.8;
        game.sound.play('jump');
    }
    
    reset() {
        this.y = this.canvas.height / 3;
        this.velocity = -1;
        this.floatOffset = 0;
    }
}