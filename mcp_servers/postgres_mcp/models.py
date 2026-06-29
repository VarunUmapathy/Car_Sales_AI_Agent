from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import String, Integer, Numeric, ForeignKey

class Base(DeclarativeBase):
    pass

class CarModel(Base):
    __tablename__ = 'car_models'
    
    model_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    make: Mapped[str] = mapped_column(String(50))
    model_name: Mapped[str] = mapped_column(String(100))
    transmission: Mapped[str] = mapped_column(String(50))
    year: Mapped[int] = mapped_column(Integer)
    Ex_Showroom_price: Mapped[float] = mapped_column(Numeric(10, 2))
    brochere_url: Mapped[str] = mapped_column(String(255), nullable=True)

class InventoryUnit(Base):
    __tablename__ = 'inventory'
    
    vin: Mapped[str] = mapped_column(String(17), primary_key=True)
    model_id: Mapped[str] = mapped_column(String(50), ForeignKey('car_models.model_id'))
    color: Mapped[str] = mapped_column(String(50))
    status: Mapped[str] = mapped_column(String(50))
    dealer_id: Mapped[str] = mapped_column(String(50))
    image_url: Mapped[str] = mapped_column(String(255), nullable=True)
    
    car_model = relationship("CarModel")