const grpc = require('@grpc/grpc-js');
const protoLoader = require('@grpc/proto-loader');
const db = require('./db');
const path = require('path');
require('dotenv').config();

const PROTO_PATH = path.join(__dirname, 'protos', 'dealership.proto');
const packageDefinition = protoLoader.loadSync(PROTO_PATH, {
  keepCase: true,
  longs: String,
  enums: String,
  defaults: true,
  oneofs: true
});

const protoDescriptor = grpc.loadPackageDefinition(packageDefinition);
const inventoryProto = protoDescriptor.dealership.v1;

const inventoryServiceImplementation = {
    GetModelsList: async (call, callback) => {
        const { make_filter } = call.request;
        try{
            let queryText = 'SELECT model_id, make, model_name, year, ex_showroom_price, brochere_url FROM car_models';
            let params = [];
            if(make_filter && make_filter.trim() != ''){
                queryText += ' WHERE make ILIKE $1';
                params.push(`%${make_filter}%`);
            }
            const res = await db.query(queryText, params);
            const models = res.rows.map(row => ({
                model_id: row.model_id,
                make: row.make,
                model_name: row.model_name,
                year: row.year,
                base_price: parseFloat(row.ex_showroom_price), 
                brochure_url: row.brochere_url || ""
            }));
            callback(null, { models: models });
        } catch (err) {
            console.error("DB Error in GetModelsList:", err);
            callback({ code: grpc.status.INTERNAL, details: "Failed to fetch car models" });
        }
    },

    CheckAvailability: async (call, callback) => {
        const { vin } = call.request;
        if (!vin) return callback({ code: grpc.status.INVALID_ARGUMENT, details: "VIN is required" });
        try {
        const queryText = `
            SELECT i.vin, i.model_id, i.color, i.status, i.image_url, c.ex_showroom_price 
            FROM inventory i
            JOIN car_models c ON i.model_id = c.model_id
            WHERE i.vin = $1
        `;
        const res = await db.query(queryText, [vin]);
        if (res.rows.length === 0) return callback({ code: grpc.status.NOT_FOUND, details: "Vehicle not found in inventory" });
        const unit = res.rows[0];   
        callback(null, {
            vin: unit.vin,
            model_id: unit.model_id,
            color: unit.color,
            actual_price: parseFloat(unit.ex_showroom_price),
            status: unit.status,
            image_url: unit.image_url || ""
        });
        } catch (err) {
            console.error("DB Error in CheckAvailability:", err);
            callback({ code: grpc.status.INTERNAL, details: "Failed to check vehicle availability" });
        }
    },

    UpdateUnitStatus: async (call, callback) => {
        const { vin, new_status } = call.request;
        if (!vin || !new_status) return callback(null, { success: false, error_message: "VIN and new_status are required" });
        const validStatuses = ['IN_STOCK', 'IN_TRANSIT', 'SOLD'];
        if (!validStatuses.includes(new_status)) return callback(null, { success: false, error_message: "Invalid status provided" });
        try {
            const res = await db.query(
                'UPDATE inventory SET status = $1 WHERE vin = $2 RETURNING vin',
                [new_status, vin]
            );
            if (res.rows.length === 0) return callback(null, { success: false, error_message: "Vehicle not found to update" });
            callback(null, { success: true, error_message: "" });
        } catch (err) {
            console.error("DB Error in UpdateUnitStatus:", err);
            callback(null, { success: false, error_message: "Database update failed" });
        }
    },

    // RPC: SearchInventory (The human way to find cars)
    SearchInventory: async (call, callback) => {
        const { model_id, color, status } = call.request;
        try {
            let queryText = `
                SELECT i.vin, i.model_id, i.color, i.status, i.image_url, c.ex_showroom_price 
                FROM inventory i
                JOIN car_models c ON i.model_id = c.model_id
                WHERE 1=1
            `;
            let params = [];
            let paramIndex = 1;
            if (model_id) {
                queryText += ` AND i.model_id = $${paramIndex++}`;
                params.push(model_id);
            }
            if (color) {
                queryText += ` AND i.color ILIKE $${paramIndex++}`;
                params.push(`%${color}%`);
            }
            if (status) {
                queryText += ` AND i.status = $${paramIndex++}`;
                params.push(status);
            } else queryText += ` AND i.status = 'IN_STOCK'`;
            const res = await db.query(queryText, params);
            const units = res.rows.map(unit => ({
                vin: unit.vin,
                model_id: unit.model_id,
                color: unit.color,
                actual_price: parseFloat(unit.ex_showroom_price),
                status: unit.status,
                image_url: unit.image_url || ""
            }));
            callback(null, { units: units });
        } catch (err) {
            console.error("DB Error in SearchInventory:", err);
            callback({ code: grpc.status.INTERNAL, details: "Failed to search inventory" });
        }
    }
}

function main() {
    const server = new grpc.Server();
    server.addService(inventoryProto.InventoryService.service, inventoryServiceImplementation);
    const PORT = process.env.PORT || 50052;
    server.bindAsync(`0.0.0.0:${PORT}`, grpc.ServerCredentials.createInsecure(), (err, port) => {
    if (err) {
        console.error("Failed to bind server:", err);
        return;
    }
    console.log(`Inventory gRPC Service running on port ${port}`);
    });
}

process.on('SIGINT', () => {
  console.log("Shutting down Inventory Service...");
  process.exit(0);
});

main();