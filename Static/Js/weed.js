// Karakter görüntüsünü yükle
const characterImage = new Image();
// Imgur'dan doğrudan görüntü URL'si
characterImage.src = 'https://i.imgur.com/yK80ovd.png'; 

console.log("Karakter görüntüsü yükleniyor...");
characterImage.onload = function() {
    console.log("✅ Karakter görüntüsü başarıyla yüklendi!");
};
characterImage.onerror = function() {
    console.error("❌ Karakter görüntüsü yüklenemedi!");
    console.log("URL formatını kontrol edin, eğer .png çalışmazsa .jpg deneyin");
    // Görüntü yüklenemezse .jpg formatını dene
    this.src = 'https://i.imgur.com/yK80ovd.jpg';
    this.onerror = function() {
        console.error("İkinci görüntü formatı da yüklenemedi!");
    };
};

class Weed {
    constructor(canvas) {
        this.canvas = canvas;
        this.x = 50;
        this.y = canvas.height / 2;
        
        // 1024x1024 görüntü için uygun boyut ayarları
        this.width = 40;   // Daha küçük görünmesi için
        this.height = 40;  // Kare oranını koruyoruz (1:1)
        
        // Çarpışma kutusu (hitbox) görüntüden biraz daha küçük olmalı
        this.hitboxReduction = 10;
        
        this.velocity = 0;
        this.gravity = 0.08;
        this.floatOffset = 0;
        this.floatSpeed = 0.05;
        
        // Yukarıda tanımlanan görüntüyü kullanın
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
        ctx.save();
        
        // Karakterin hareketi için açı hesaplama
        let angle = 0;
        if (this.velocity < 0) {
            angle = -Math.PI/15; // Yukarı hareket ederken yukarı bak
        } else if (this.velocity > 1) {
            angle = Math.PI/15;  // Aşağı hareket ederken aşağı bak
        }
        
        ctx.translate(this.x, this.y);
        ctx.rotate(angle);
        
        // Görüntüyü kontrol et ve çiz
        if (this.image.complete && this.image.naturalHeight !== 0) {
            // Görüntü yüklendiyse çiz
            ctx.drawImage(
                this.image, 
                -this.width/2, 
                -this.height/2, 
                this.width, 
                this.height
            );
            
            // Hata ayıklama: çarpışma kutusunu göster (geliştirme sırasında açabilirsiniz)
            /*
            ctx.strokeStyle = 'red';
            ctx.strokeRect(
                -this.width/2 + this.hitboxReduction, 
                -this.height/2 + this.hitboxReduction, 
                this.width - this.hitboxReduction*2, 
                this.height - this.hitboxReduction*2
            );
            */
        } else {
            // Görüntü yoksa yedek çizim yap
            this.drawFallbackCharacter(ctx);
        }
        
        ctx.restore();
    }
    
    // Yedek çizim metodu
    drawFallbackCharacter(ctx) {
        // Basit karakter çizimi
        ctx.fillStyle = '#44A244';
        ctx.beginPath();
        ctx.ellipse(0, 0, this.width/2, this.height/2, 0, 0, Math.PI * 2);
        ctx.fill();
        
        ctx.strokeStyle = '#2E7D32';
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.moveTo(-this.width/3, 0);
        ctx.lineTo(this.width/3, 0);
        ctx.stroke();
        
        ctx.beginPath();
        ctx.moveTo(0, -this.height/3);
        ctx.lineTo(0, this.height/3);
        ctx.stroke();
    }
    
    jump() {
        this.velocity = -3.8;
        playSound('jump'); // Inline script kullanıyorsanız
        // Eğer ayrı dosyalar kullanıyorsanız: game.sound.play('jump');
    }
    
    reset() {
        this.y = this.canvas.height / 3;
        this.velocity = -1;
        this.floatOffset = 0;
    }
}