from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .database import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(String, nullable=False, default="seller")
    musicians = relationship("Musician", back_populates="creator", foreign_keys="Musician.created_by")
    discs = relationship("Disc", back_populates="creator", foreign_keys="Disc.created_by")
    sales = relationship("Sale", back_populates="seller", foreign_keys="Sale.seller_id")
    
    def __repr__(self):
        return f"<User(id={self.id}, username={self.username}, role={self.role})>"

class Musician(Base):
    __tablename__ = "musicians"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    genre = Column(String, nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    creator = relationship("User", back_populates="musicians", foreign_keys=[created_by])
    discs = relationship("Disc", back_populates="musician", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Musician(id={self.id}, name={self.name})>"

class Disc(Base):
    __tablename__ = "discs"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    musician_id = Column(Integer, ForeignKey("musicians.id"), nullable=False)
    price = Column(Float, nullable=False)
    stock = Column(Integer, nullable=False, default=0)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    musician = relationship("Musician", back_populates="discs")
    creator = relationship("User", back_populates="discs", foreign_keys=[created_by])
    sales = relationship("Sale", back_populates="disc", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Disc(id={self.id}, title={self.title}, stock={self.stock})>"

class Sale(Base):
    __tablename__ = "sales"
    
    id = Column(Integer, primary_key=True, index=True)
    disc_id = Column(Integer, ForeignKey("discs.id"), nullable=False)
    quantity = Column(Integer, nullable=False)
    total_price = Column(Float, nullable=False)
    sold_at = Column(DateTime(timezone=True), server_default=func.now())
    seller_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    disc = relationship("Disc", back_populates="sales")
    seller = relationship("User", back_populates="sales", foreign_keys=[seller_id])

    def __repr__(self):
        return f"<Sale(id={self.id}, disc_id={self.disc_id}, quantity={self.quantity})>"