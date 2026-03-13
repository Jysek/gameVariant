"""
Boss — ZERO flash overlay. Nessuna box bianca o rossa visibile.
All'hit: lo sprite viene semplicemente ridisegnato leggermente più brillante
tramite un tint alpha sulla stessa posizione — invisibile come box.
"""
import random
import pygame
from core.constants import SCREEN_WIDTH, WHITE, RED, GREEN, YELLOW, ORANGE
from core.assets import Assets
from entities.laser import Laser

class Boss:
    def __init__(self):
        self.width=200; self.height=94
        self.x=float(SCREEN_WIDTH//2-self.width//2); self.y=float(-self.height)
        self.target_y=30; self.entering=True; self.alive=True
        self.max_hp=60; self.hp=self.max_hp
        self.h_speed=random.choice([-2.5,-2.0,-1.5,1.5,2.0,2.5])
        self.h_dir_timer=0; self.h_dir_interval=random.randint(120,300)
        self.frames=Assets.boss_frames
        self.frame_idx=0; self.frame_timer=0; self.frame_delay=6
        self.cannon_offsets=[(0.12,0.85),(0.38,0.95),(0.62,0.95),(0.88,0.85)]
        self.shoot_timer=0; self.shoot_interval=40
        # Hit: solo cambio di luminosità, NESSUNA surface sovrapposta
        self.hit_flash=0; self.hit_flash_max=8

    def update(self):
        if not self.alive: return []
        if self.entering:
            self.y+=1.5
            if self.y>=self.target_y: self.y=float(self.target_y); self.entering=False
            return []
        self.x+=self.h_speed
        self.h_dir_timer+=1
        if self.h_dir_timer>=self.h_dir_interval:
            self.h_speed=random.choice([-2.5,-2.0,-1.5,1.5,2.0,2.5])
            self.h_dir_timer=0; self.h_dir_interval=random.randint(120,300)
        if self.x<=10: self.x=10.0; self.h_speed=abs(self.h_speed)
        elif self.x>=SCREEN_WIDTH-self.width-10:
            self.x=float(SCREEN_WIDTH-self.width-10); self.h_speed=-abs(self.h_speed)
        self.frame_timer+=1
        if self.frame_timer>=self.frame_delay:
            self.frame_timer=0; self.frame_idx=(self.frame_idx+1)%len(self.frames)
        if self.hit_flash>0: self.hit_flash-=1
        self.shoot_timer+=1
        if self.shoot_timer>=self.shoot_interval:
            self.shoot_timer=0; return self._fire()
        return []

    def _fire(self):
        p=random.randint(0,2); lasers=[]
        if p==0:
            for ox,oy in self.cannon_offsets:
                lasers.append(Laser(self.x+int(self.width*ox)-2,self.y+int(self.height*oy),5,ORANGE,is_enemy=True))
        elif p==1:
            for i in [0,3]:
                ox,oy=self.cannon_offsets[i]
                lasers.append(Laser(self.x+int(self.width*ox)-2,self.y+int(self.height*oy),6,RED,is_enemy=True))
        else:
            for i in [1,2]:
                ox,oy=self.cannon_offsets[i]
                lasers.append(Laser(self.x+int(self.width*ox)-2,self.y+int(self.height*oy),7,YELLOW,is_enemy=True))
        return lasers

    def take_damage(self,amount=1):
        self.hp-=amount; self.hit_flash=self.hit_flash_max
        if self.hp<=0: self.hp=0; self.alive=False; return True
        return False

    def draw(self,surf):
        if not self.alive: return
        frame=self.frames[self.frame_idx]
        scaled=pygame.transform.scale(frame,(self.width,self.height))
        # Hit flash: aumenta luminosità con alpha leggermente più alta — NO box
        if self.hit_flash>0:
            ratio=self.hit_flash/self.hit_flash_max
            # Scala leggermente lo sprite (pulsazione sottile, no overlay colorato)
            pulse=int(4*ratio)
            w2=self.width+pulse*2; h2=self.height+pulse*2
            scaled=pygame.transform.scale(frame,(w2,h2))
            surf.blit(scaled,(int(self.x)-pulse,int(self.y)-pulse))
        else:
            surf.blit(scaled,(int(self.x),int(self.y)))

    def draw_health_bar(self,surf):
        if not self.alive: return
        bw,bh=400,16; bx=SCREEN_WIDTH//2-bw//2; by=8
        pygame.draw.rect(surf,(12,12,18),(bx-1,by-1,bw+2,bh+2))
        pygame.draw.rect(surf,(40,40,55),(bx,by,bw,bh))
        pct=self.hp/self.max_hp
        col=GREEN if pct>0.5 else(YELLOW if pct>0.25 else RED)
        fw=int(bw*pct)
        if fw>0: pygame.draw.rect(surf,col,(bx,by,fw,bh))
        for s in range(1,4):
            sx=bx+bw*s//4
            pygame.draw.line(surf,(12,12,18),(sx,by),(sx,by+bh),1)
        font=pygame.font.Font(None,20)
        label=font.render(f"BOSS  {self.hp}/{self.max_hp}",True,WHITE)
        surf.blit(label,(bx+bw//2-label.get_width()//2,by+1))

    def get_rect(self):
        return pygame.Rect(self.x+15,self.y+10,self.width-30,self.height-15)
