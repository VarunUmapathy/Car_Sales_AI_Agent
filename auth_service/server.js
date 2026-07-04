const grpc = require('@grpc/grpc-js');
const protoLoader = require('@grpc/proto-loader');
const jwt = require('jsonwebtoken');
const jwksClient = require('jwks-rsa');
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
const authProto = protoDescriptor.dealership.v1;

const client = jwksClient({
    jwksUri: `https://${process.env.AUTH0_DOMAIN}/.well-known/jwks.json`
});

function getKey(header, callback){
    client.getSigningKey(header.kid, function(err, key){
        if (err) return callback(err);
        const signingKey = key.publicKey || key.rsaPublicKey;
        callback(null, signingKey);
    });
}

const authServiceImplementation = {
    ValidateToken: async (call, callback) => {
        const token = call.request.token;
        if (!token) return callback(null, { is_valid: false, error_message: "No token provided" });
        jwt.verify(token, getKey, { algorithms: ['RS256']}, async (err, decoded) => {
            if (err) return callback(null, { is_valid: false, error_message: `Invalid token: ${err.message}` });
            try {
            const ssoUserId = decoded.sub; 
            const res = await db.query(
            'SELECT agent_id, sso_user_id, email, name, role FROM agents WHERE sso_user_id = $1',
            [ssoUserId]
            );
            if (res.rows.length === 0) {
            return callback(null, { is_valid: false, error_message: "Agent not found in CRM database" });
            }
            const agent = res.rows[0];
            callback(null, {
                agent_id: agent.agent_id,
                sso_user_id: agent.sso_user_id,
                email: agent.email,
                name: agent.name,
                role: agent.role,
                is_valid: true,
                error_message: ""
            });

        } catch (dbErr) {
            console.error("DB Error:", dbErr);
            callback(null, { is_valid: false, error_message: "Internal database error" });
        }
        });
    },

    CheckAgentPermissions: async (call, callback) => {
        const { agent_id, required_role } = call.request;
        try {
            const res = await db.query('SELECT role FROM agents WHERE agent_id = $1', [agent_id]);
            
            if (res.rows.length === 0) {
                return callback(null, { has_permission: false });
            }

            const agentRole = res.rows[0].role;
            // Simple exact match logic. You can expand this for hierarchical roles (e.g., Manager overrides Agent)
            const hasPermission = (agentRole === required_role || agentRole === 'Manager');
            
            callback(null, { has_permission: hasPermission });
        } catch (err) {
            console.error(err);
            callback({ code: grpc.status.INTERNAL, details: "Database error" });
        }
    },

    GetAgentProfile: async (call, callback) => {
        const { agent_id } = call.request;
        try {
        const res = await db.query(
            'SELECT agent_id, name, email, role, is_online FROM agents WHERE agent_id = $1',
            [agent_id]
        );

        if (res.rows.length === 0) {
            return callback({ code: grpc.status.NOT_FOUND, details: "Agent not found" });
        }

        callback(null, res.rows[0]);
        } catch (err) {
            console.error(err);
            callback({ code: grpc.status.INTERNAL, details: "Database error" });
        }
    }
};

function main() {
    const server = new grpc.Server();
    server.addService(authProto.AuthService.service, authServiceImplementation);
    const PORT = process.env.PORT || 50051;
    server.bindAsync(`0.0.0.0:${PORT}`, grpc.ServerCredentials.createInsecure(), (err, port) => {
        if (err) {
            console.error("Failed to bind server:", err);
            return;
        }
        console.log(`Auth gRPC Service running on port ${port}`);
    });
}

process.on('SIGINT', async () => {
  console.log("Shutting down Auth Service...");
  process.exit(0);
});

main();