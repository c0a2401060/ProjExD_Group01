import math
import os
import random
import sys
import time
import wave
import pygame as pg


WIDTH = 600  # ゲームウィンドウの幅
HEIGHT =700  # ゲームウィンドウの高さ
os.chdir(os.path.dirname(os.path.abspath(__file__)))


def check_bound(obj_rct: pg.Rect) -> tuple[bool, bool]:
    """
    オブジェクトが画面内or画面外を判定し，真理値タプルを返す関数
    引数：こうかとんや爆弾，ビームなどのRect
    戻り値：横方向，縦方向のはみ出し判定結果（画面内：True／画面外：False）
    """
    yoko, tate = True, True
    if obj_rct.left < 0 or WIDTH < obj_rct.right:
        yoko = False
    if obj_rct.top < 0 or HEIGHT < obj_rct.bottom:
        tate = False
    return yoko, tate


def calc_orientation(org: pg.Rect, dst: pg.Rect) -> tuple[float, float]:
    """
    orgから見て，dstがどこにあるかを計算し，方向ベクトルをタプルで返す
    引数1 org：爆弾SurfaceのRect
    引数2 dst：こうかとんSurfaceのRect
    戻り値：orgから見たdstの方向ベクトルを表すタプル
    """
    x_diff, y_diff = dst.centerx-org.centerx, dst.centery-org.centery
    norm = math.sqrt(x_diff**2+y_diff**2)
    if norm < 2:
        return(0,1)
    return x_diff/norm, y_diff/norm


class Bird(pg.sprite.Sprite):
    """
    ゲームキャラクター（こうかとん）に関するクラス
    """
    delta = {  # 押下キーと移動量の辞書
        pg.K_UP: (0, -1),
        pg.K_DOWN: (0, +1),
        pg.K_LEFT: (-1, 0),
        pg.K_RIGHT: (+1, 0),
    }

    def __init__(self, num: int, xy: tuple[int, int]):
        """
        こうかとん画像Surfaceを生成する
        引数1 num：こうかとん画像ファイル名の番号
        引数2 xy：こうかとん画像の位置座標タプル
        """
        super().__init__()
        img0 = pg.transform.rotozoom(pg.image.load(f"fig/{num}.png"), 0, 0.5)
        img = pg.transform.flip(img0, True, False)  # デフォルトのこうかとん
        self.imgs = {
            (+1, 0): img,  # 右
            (+1, -1): pg.transform.rotozoom(img, 45, 0.9),  # 右上
            (0, -1): pg.transform.rotozoom(img, 90, 0.9),  # 上
            (-1, -1): pg.transform.rotozoom(img0, -45, 0.9),  # 左上
            (-1, 0): img0,  # 左
            (-1, +1): pg.transform.rotozoom(img0, 45, 0.9),  # 左下
            (0, +1): pg.transform.rotozoom(img, -90, 0.9),  # 下
            (+1, +1): pg.transform.rotozoom(img, -45, 0.9),  # 右下

        }
        self.dire = (+1, 0)
        self.image = self.imgs[self.dire]
        self.rect = self.image.get_rect()
        self.rect.center = xy
        self.speed = 10

    def change_img(self, num: int, screen: pg.Surface):
        """
        こうかとん画像を切り替え，画面に転送する
        引数1 num：こうかとん画像ファイル名の番号
        引数2 screen：画面Surface
        """
        self.image = pg.transform.rotozoom(pg.image.load(f"fig/{num}.png"), 0, 0.5)
        self.image = pg.transform.rotozoom(pg.image.load(f"fig/{num}.png"), 0, 0.5)
        screen.blit(self.image, self.rect)

    def update(self, key_lst: list[bool], screen: pg.Surface):
        """
        押下キーに応じてこうかとんを移動させる
        引数1 key_lst：押下キーの真理値リスト
        引数2 screen：画面Surface
        """
        sum_mv = [0, 0]
        for k, mv in __class__.delta.items():
            if key_lst[k]:
                sum_mv[0] += mv[0]
                sum_mv[1] += mv[1]
            
            if key_lst[pg.K_LSHIFT]:  # 左Shiftを押しているとき低速化
                self.speed = 3
            else:
                self.speed = 10

        self.rect.move_ip(self.speed*sum_mv[0], self.speed*sum_mv[1])
        if check_bound(self.rect) != (True, True):
            self.rect.move_ip(-self.speed*sum_mv[0], -self.speed*sum_mv[1])
        if not (sum_mv[0] == 0 and sum_mv[1] == 0):
            self.dire = tuple(sum_mv)
            self.image = self.imgs[self.dire]
        screen.blit(self.image, self.rect)


class Bomb(pg.sprite.Sprite):
    """
    爆弾に関するクラス
    """
    colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0), (255, 0, 255), (0, 255, 255)]

    def __init__(self, emy: "Enemy", bird: Bird, tmr:int, bullet:tuple[float,float]=None,):
        """
        爆弾円Surfaceを生成する
        引数1 emy：爆弾を投下する敵機
        引数2 bird：攻撃対象のこうかとん
        引数3 tmr：攻撃方法変更時の参照時間
        引数4 bullet：弾べクトルの方向を表すタプル
        """
        super().__init__()
        if 4500 < tmr <= 9000: #時間が90秒から180秒の間なら爆弾の大きさをランダムにする
            rad =random.randint(5,11)
        else: #時間が90秒までなら爆弾の大きさを13に固定する
            rad = 13
        self.image = pg.Surface((2*rad, 2*rad))
        color = random.choice(__class__.colors)  # 爆弾円の色：クラス変数からランダム選択
        pg.draw.circle(self.image, color, (rad, rad), rad)
        self.image.set_colorkey((0, 0, 0))
        self.rect = self.image.get_rect()
        # 爆弾を投下するemyから見た攻撃対象のbirdの方向を計算
        self.vx, self.vy = calc_orientation(emy.rect, bird.rect)

        if 4500 < tmr <= 9000: #時間が90秒から180秒の間なら爆弾の動きをランダムに動かす
            i = random.randint(0,3)
            if i==0: # 1/3の確率でランダムにボムを飛ばす
                self.vx, self.vy = random.randint(-1,1), random.randint(0,1)
                if self.vx == 0 and self.vy == 0: # どちらも0だった場合に、どちらかが0じゃなくなるまでランダムを回し続ける
                    while True:
                        self.vx, self.vy = random.randint(-1,1), random.randint(0,1)
                        if self.vx != 0 or self.vy != 0:
                            break
            else: # 2/3の確率でこうかとんに向けてボムを飛ばす
                self.vx,self.vy = calc_orientation(emy.rect,bird.rect)

        self.rect.centerx = emy.rect.centerx
        self.rect.centery = emy.rect.centery+emy.rect.height//2
        if 0 < tmr <= 4500: #時間が90秒以下の時
            if bullet :#弾べクトルの方向を引数で受け取る
                self.vx,self.vy = bullet
            else: # 自機にに向けて発射する
                self.vx,self.vy = calc_orientation(emy.rect,bird.rect)
        self.speed = 9

    def update(self,tmr:int):
        """
        爆弾を速度ベクトルself.vx, self.vyに基づき移動させる
        引数 screen：画面Surface
        引数 tmr：時間経過に伴った反射・消滅の仕様変更
        """
        if 4500 < tmr <= 9000: #時間が90秒から180秒の間なら爆弾の動きを遅くする
            j = random.randint(3,8)
            self.speed = j
            self.rect.move_ip(self.speed*self.vx, self.speed*self.vy)
        
        else: #時間が90秒未満なら爆弾の動きは通常
            self.rect.move_ip(self.speed*self.vx, self.speed*self.vy)

        
        if check_bound(self.rect) != (True, True):
            if 4500 < tmr <= 9000: #時間が90秒から180秒なら爆弾の動きは反射
                self.vx *= -1
                self.vy *= -1
                self.rect.move_ip(self.speed*self.vx, self.speed*self.vy)

            if tmr <= 4500: # 時間が90秒未満なら画面端で消滅
                self.rect.move_ip(self.speed*self.vx, self.speed*self.vy)
                self.kill()


class Beam(pg.sprite.Sprite):
    """
    ビームに関するクラス
    残してあるが使う予定なし
    """
    def __init__(self, bird: Bird):
        """
        ビーム画像Surfaceを生成する
        引数 bird：ビームを放つこうかとん
        """
        super().__init__()
        self.vx, self.vy = bird.dire
        angle = math.degrees(math.atan2(-self.vy, self.vx))
        self.image = pg.transform.rotozoom(pg.image.load(f"fig/beam.png"), angle, 1.0)
        self.vx = math.cos(math.radians(angle))
        self.vy = -math.sin(math.radians(angle))
        self.rect = self.image.get_rect()
        self.rect.centery = bird.rect.centery+bird.rect.height*self.vy
        self.rect.centerx = bird.rect.centerx+bird.rect.width*self.vx
        self.speed = 10

    def update(self):
        """
        ビームを速度ベクトルself.vx, self.vyに基づき移動させる
        引数 screen：画面Surface
        """
        self.rect.move_ip(self.speed*self.vx, self.speed*self.vy)
        if check_bound(self.rect) != (True, True):
            self.kill()

class Explosion(pg.sprite.Sprite):
    """
    爆発に関するクラス
    """
    def __init__(self, obj: "Bomb|Enemy", life: int):
        """
        爆弾が爆発するエフェクトを生成する
        引数1 obj：爆発するBombまたは敵機インスタンス
        引数2 life：爆発時間
        """
        super().__init__()
        img = pg.image.load(f"fig/explosion.gif")
        self.imgs = [img, pg.transform.flip(img, 1, 1)]
        self.image = self.imgs[0]
        self.rect = self.image.get_rect(center=obj.rect.center)
        self.life = life

    def update(self):
        """
        爆発時間を1減算した爆発経過時間_lifeに応じて爆発画像を切り替えることで
        爆発エフェクトを表現する
        """
        self.life -= 1
        self.image = self.imgs[self.life//10%2]
        if self.life < 0:
            self.kill()


class Enemy(pg.sprite.Sprite):
    """
    敵機に関するクラス
    """
    imgs = [pg.image.load(f"fig/alien{2}.png") for i in range(1, 4)]
    
    def __init__(self, tmr):
        super().__init__()
        self.image = pg.transform.rotozoom(random.choice(__class__.imgs), 0, 2)
        self.rect = self.image.get_rect()
        self.rect.center = ((WIDTH - 128) / 1.7, HEIGHT /7)
        self.vx, self.vy = 0, +6
        self.bound = random.randint(50, HEIGHT//8)  # 停止位置
        self.state = "down"  # 降下状態or停止状態
        if tmr < 4500:#時間が90秒未満なら爆弾インターバルを短く
            self.interval = random.randint(40, 45)  # 爆弾投下インターバルをランダムに指定する

        if 4500 < tmr <= 9000: #時間が90秒から180秒なら爆弾インターバルを短く
            self.interval =5

    def three_Bombs(self,bird,tmr) -> list:
        """
        自機狙いをする弾と左右にランダムに動く弾を生成し返す。
        引数:bird Birdインスタンス
        戻り値:Bombインスタンスのリスト        
        """
        bombs =[Bomb(self,bird,tmr)] #自機を狙う
        count =0
        while count < random.randint(5,15):
                    angle = random.uniform(-math.pi/3,math.pi/3) #ランダムに左右に弾を放つ
                    vx = math.sin(angle) #
                    vy = math.cos(angle) #
                    norm = math.hypot(vx,vy)
                    if norm == 0:
                        continue #無効なベクトルをスキップ
                    bombs.append(Bomb(self,bird,tmr,bullet=(vx/norm,vy/norm)))
                    count +=1
        # print(f"three_Bombs: 実際に返す弾の数 = {len(bombs)}") #ここで出てる弾の数を確認できる
        return bombs

    def update(self):
        """
        敵機を速度ベクトルself.vyに基づき移動（降下）させる
        ランダムに決めた停止位置_boundまで降下したら，_stateを停止状態に変更する
        引数 screen：画面Surface
        """
        if self.rect.centery > self.bound:
            self.vy = 0
            self.state = "stop"
        self.rect.move_ip(self.vx, self.vy)

class Score:
    """
    必殺技の使用回数についてのクラス
    """
    def __init__(self):
        """
        必殺技の残り使用回数を画面上に表示する
        """
        self.font = pg.font.Font(None, 50)
        self.color = (255, 0, 0)
        self.value = 3
        self.image = self.font.render(f"Bomb: *\{self.value}/b*", 0, self.color)
        self.rect = self.image.get_rect()
        self.rect.center = 500, HEIGHT-50

    def update(self, screen: pg.Surface):
        """
        必殺技の回数を変更する
        引数 screen：画面Surface
        """
        self.image = self.font.render(f"Bomb: *\{self.value}/*", 0, self.color)
        screen.blit(self.image, self.rect)

class hissatu(pg.sprite.Sprite):
    """
    Bキー押下で敵の攻撃を爆発エフェクトとともに数秒間消滅させる
    """
    def __init__(self,life:int):
        super().__init__()
        self.image = pg.Surface((WIDTH,HEIGHT))
        self.rect = self.image.get_rect()
        pg.draw.rect(self.image,(255,0,255),(0,0,WIDTH,HEIGHT))
        self.life = life
        self.image.set_alpha(80)

    def update(self):
        """
        必殺時間を1減算した必殺経過時間_lifeに応じてSurfaceを切り替えることで
        必殺エフェクトを表現する
        """
        self.life -= 1
        if self.life < 0:
            self.kill()

    


class Time:
    """
    制限時間を表示するクラス
    制限時間：60秒
    """
    def __init__(self):
        """
        制限時間を画面上に表示する
        """
        self.font = pg.font.Font(None, 50)
        self.color = (255, 255, 255)
        self.value = 180
        self.image = self.font.render(f"Time: {self.value}", 0, self.color)
        self.rect = self.image.get_rect()
        self.rect.center = 300, HEIGHT-50

    def update(self, screen: pg.Surface):
        """
        残り時間の秒数を変更する
        引数 screen：画面Surface
        """
        self.image = self.font.render(f"Time: {self.value}", 0, self.color)
        screen.blit(self.image, self.rect)   

bird = Bird(3, (300, 400))
img1 = pg.Surface((WIDTH, HEIGHT))
img1.set_alpha((180))

def gameclear(screen: pg.Surface) -> None:
        """
        制限時間まで生き延びた場合にクリア画面を表示する
        引数 screen：画面Surface
        """
        pg.mixer.music.stop()
        screen.blit(img1,(0, 0))  # ブラックアウト
        pg.draw.rect(img1, (0, 0, 0), (0, 0, WIDTH, HEIGHT))
        img2 =  pg.image.load("fig/9.png")
        bird.change_img(9, screen)
        fonto = pg.font.Font(None, 80)
        txt = fonto.render("Game clear!", True, (255, 0, 0))
        screen.blit(txt, [147, 250])  # テキストの表示
        screen.blit(img2, [280, 330])  # こうかとんの表示
        pg.display.update()
        time.sleep(4)
        return

def main():
    pg.display.set_caption("死ぬなこうかとん‼")
    screen = pg.display.set_mode((WIDTH, HEIGHT))
    bg_img = pg.image.load(f"fig/bg_boss.jpg")

    battle_BGM = f"fig/Eye-for-an-EyeT.wav"
    with wave.open(battle_BGM,"rb") as f:
        channels =f.getnchannels()
        width = f.getsampwidth()
        rate = f.getframerate()
    pg.mixer.init(frequency=rate,size=-width*8,channels=channels)
    pg.mixer.music.load(battle_BGM)
    pg.mixer.music.play()

    get_time = Time()

    bird = Bird(3, (300, 400))
    bombs = pg.sprite.Group()
    exps = pg.sprite.Group()
    emys = pg.sprite.Group()
    gras = pg.sprite.Group()

    score = Score()

    # ゲームオーバー画面
    ck_img = pg.image.load("fig/8.png")  # 泣いているこうかとん画像
    bo_img = pg.Surface((WIDTH, HEIGHT))  # ブラックアウト画面
    pg.draw.rect(bo_img, (0,0,0),pg.Rect(0,0,WIDTH,HEIGHT))
    bo_img.set_alpha(170) 
    fonto = pg.font.Font(None,80)  # 文字
    txt = fonto.render("Game Over",True, (255,255,255))


    # time = Time()
    tmr = 0
    clock = pg.time.Clock()
    while True:

        if tmr % 50 == 0:  #1秒ずつ減る
            get_time.value-=1

        if get_time.value <= 10 :
            get_time.color = (255, 0, 0)
            if tmr % 5 == 0:
                get_time.color = (255, 255, 255)
                


        key_lst = pg.key.get_pressed()
        for event in pg.event.get():
            if event.type == pg.QUIT:
                return 0
            if event.type == pg.KEYDOWN and event.key == pg.K_b:
                if score.value>0:
                    gra = hissatu(50)
                    gras.add(gra)
                    score.value -= 1
        screen.blit(bg_img, [0, 0])

        if tmr%8000 == 0:
            emys.add(Enemy(tmr))

        # if tmr%200 == 0 and tmr < 1500:  # 200フレームに1回，敵機を出現させる
        #     emys.add(Enemy(tmr))
        
        # if tmr%100 ==0 and 1500 < tmr <= 3000: # 100フレームに1回，敵機を出現させる
        #     emys.add(Enemy(tmr))

        for emy in emys:
            if emy.state == "stop" and tmr%emy.interval == 0:
                if 0 < tmr <= 4500:
                    for b in emy.three_Bombs(bird,tmr):
                        bombs.add(b)
                else:
                    bombs.add(Bomb(emy,bird,tmr))
                # 敵機が停止状態に入ったら，intervalに応じて爆弾投下


        for bomb in pg.sprite.spritecollide(bird, bombs, True):  # こうかとんと衝突した爆弾リスト
            gameover(screen)
            score.update(screen)
            pg.display.update()
            return
        
        for bomb in pg.sprite.groupcollide(bombs, gras, True, False).keys():
            exps.add(Explosion(bomb, 50))
            bird.change_img(6, screen)

        gras.update()
        gras.draw(screen)
        bird.update(key_lst, screen)
        emys.update()
        emys.draw(screen)
        bombs.update(tmr)
        bombs.draw(screen)
        exps.update()
        exps.draw(screen)
        score.update(screen)
        get_time.update(screen)  
        pg.display.update()
        tmr += 1
        clock.tick(50)

        if tmr == 9000:  #  0秒で終了
            gameclear(screen)
            return
        
        def gameover(screen: pg.surface) -> None:
            """
            こうかとんが攻撃にヒットした場合にゲームオーバー画面を表示する
            引数 screen：画面Surface
            """ 
            pg.mixer.music.stop()
            screen.blit(bo_img, [0, 0])
            screen.blit(txt, [147,250])
            screen.blit(ck_img,[280,330])
            pg.display.update()
            time.sleep(3)
            return
        

        


if __name__ == "__main__":
    pg.init()
    main()
    pg.quit()
    sys.exit()
