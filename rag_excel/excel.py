from openpyxl import Workbook

wb=Workbook()
ws=wb.active
ws.title="Orders"
ws.append(["OrderID","Customer","Product","Category","Quantity","UnitPrice","OrderDate","Region","Salesperson","Status"])
rows=[
["O1001","Acme","Laptop","Electronics",5,1200,"2024-01-15","North","Alice","Delivered"],
["O1002","Beta","Mouse","Electronics",20,25,"2024-02-10","South","Bob","Delivered"],
["O1003","Gamma","Desk","Furniture",3,350,"2024-03-05","East","Alice","Pending"],
["O1004","Delta","Chair","Furniture",10,120,"West","Chris","Delivered"],
["O1005","Acme","Monitor","Electronics",8,300,"North","Dana","Cancelled"],
["O1006","Echo","Printer","Electronics",4,450,"South","Bob","Delivered"],
["O1007","Foxtrot","Notebook","Stationery",100,4,"East","Chris","Delivered"],
["O1008","Gamma","Pen","Stationery",250,1.5,"West","Dana","Pending"],
["O1009","Hotel","Laptop","Electronics",2,1250,"North","Alice","Delivered"],
["O1010","India","Desk","Furniture",6,340,"South","Chris","Delivered"],
["O1011","Juliet","Monitor","Electronics",7,310,"East","Bob","Delivered"],
["O1012","Kilo","Chair","Furniture",12,115,"West","Dana","Pending"],
]
for r in rows: ws.append(r)
path="sales_orders.xlsx"
wb.save(path)
print(path)
