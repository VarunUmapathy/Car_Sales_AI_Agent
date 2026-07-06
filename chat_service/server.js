const grpc = require('@grpc/grpc-js');
const protoLoader = require('@grpc/proto-loader');
const crypto = require('crypto');
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
const chatProto = protoDescriptor.dealership.v1;

const chatServiceImplementation = {
    GetSessionStatus: async (call, callback) => {
        const { session_id } = call.request;
        try {
            const res = await db.query(
                'SELECT status, agent_id FROM chat_sessions WHERE session_id = $1',
                [session_id]
            );
            if (res.rows.length === 0) return callback({ code: grpc.status.NOT_FOUND, details: "Session not found" });
            const session = res.rows[0];
            callback(null, {
                status: session.status || 'UNKNOWN',
                assigned_agent_id: session.agent_id || ""
            });
        } catch (err) {
            console.error("DB Error in GetSessionStatus:", err);
            callback({ code: grpc.status.INTERNAL, details: "Database error" });
        }
    },
    
    SaveHumanMessage: async (call, callback) => {
        const { session_id, agent_id, message_text } = call.request;
        if (!session_id || !agent_id || !message_text) return callback({ code: grpc.status.INVALID_ARGUMENT, details: "Missing required fields" });
        try {
            const messageId = crypto.randomUUID();
            const senderType = 'AGENT'; 
            const res = await db.query(
                `INSERT INTO messages (message_id, session_id, sender_type, sender_id, message_text) 
                VALUES ($1, $2, $3, $4, $5) RETURNING created_at`,
                [messageId, session_id, senderType, agent_id, message_text]
            );
            callback(null, {
                message_id: messageId,
                success: true,
                timestamp: res.rows[0].created_at.toISOString()
            });
        } catch (err) {
            console.error("DB Error in SaveHumanMessage:", err);
            callback(null, { message_id: "", success: false, timestamp: "" });
        }
    },

    UpdateSessionAgent: async (call, callback) => {
        const { session_id, agent_id } = call.request;
        if (!session_id || !agent_id) return callback(null, { success: false, error_message: "Missing session_id or agent_id" });
        try {
            const res = await db.query(
                `UPDATE chat_sessions 
                SET agent_id = $1, status = 'HUMAN_ACTIVE', updated_at = NOW() 
                WHERE session_id = $2 AND (agent_id IS NULL OR agent_id = $1) 
                RETURNING session_id`,
                [agent_id, session_id]
            );
            if (res.rows.length === 0) {
                return callback(null, { 
                success: false, 
                error_message: "Conflict: Session already claimed by another agent or does not exist." 
                });
            }
            callback(null, { success: true, error_message: "" });
        } catch (err) {
            console.error("DB Error in UpdateSessionAgent:", err);
            callback(null, { success: false, error_message: "Internal database error" });
        }
    },

    GetSessionsList: async (call, callback) => {
        const { status, assigned_agent_id } = call.request;
        try {
            let queryText = 'SELECT session_id, contact_id, status, agent_id, updated_at FROM chat_sessions WHERE 1=1';
            let params = [];
            let paramIndex = 1;
            if (status) {
                queryText += ` AND status = $${paramIndex++}`;
                params.push(status);
            }
            if (assigned_agent_id) {
                queryText += ` AND agent_id = $${paramIndex++}`;
                params.push(assigned_agent_id);
            }
            queryText += ' ORDER BY updated_at DESC';
            const res = await db.query(queryText, params);
            const sessions = res.rows.map(row => ({
                session_id: row.session_id,
                contact_id: row.contact_id || "",
                status: row.status || "UNKNOWN",
                assigned_agent_id: row.agent_id || "",
                updated_at: row.updated_at ? row.updated_at.toISOString() : ""
            }));

            callback(null, { sessions });
        } catch (err) {
            console.error("DB Error in GetSessionsList:", err);
            callback({ code: grpc.status.INTERNAL, details: "Failed to fetch chat sessions" });
        }
    },

    // RPC: GetSessionMessages
    GetSessionMessages: async (call, callback) => {
        const { session_id } = call.request;

        if (!session_id) {
        return callback({ code: grpc.status.INVALID_ARGUMENT, details: "Session ID required" });
        }

        try {
        // Order ascending so the chat history flows top-to-bottom naturally
        const res = await db.query(
            'SELECT message_id, sender_type, sender_id, message_text, created_at FROM messages WHERE session_id = $1 ORDER BY created_at ASC',
            [session_id]
        );

        const messages = res.rows.map(row => ({
            message_id: row.message_id,
            sender_type: row.sender_type,
            sender_id: row.sender_id || "",
            message_text: row.message_text,
            timestamp: row.created_at ? row.created_at.toISOString() : ""
        }));

        callback(null, { messages });
        } catch (err) {
        console.error("DB Error in GetSessionMessages:", err);
        callback({ code: grpc.status.INTERNAL, details: "Failed to fetch chat messages" });
        }
    }
};

function main() {
    const server = new grpc.Server();
    server.addService(chatProto.ChatService.service, chatServiceImplementation);
    const PORT = process.env.PORT || 50053;
    server.bindAsync(`0.0.0.0:${PORT}`, grpc.ServerCredentials.createInsecure(), (err, port) => {
    if (err) {
        console.error("Failed to bind server:", err);
        return;
    }
    console.log(`Chat gRPC Service running on port ${port}`);
    });
}

process.on('SIGINT', () => {
  console.log("Shutting down Chat Service...");
  process.exit(0);
});

main();