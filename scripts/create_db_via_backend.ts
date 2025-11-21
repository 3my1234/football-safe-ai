/**
 * Create Football AI database using your Rolley backend's PostgreSQL connection
 * Run from backend directory: npx ts-node football-safe-ai/scripts/create_db_via_backend.ts
 */
import { PrismaClient } from '@prisma/client';
import * as dotenv from 'dotenv';
import path from 'path';

// Load .env from backend directory
dotenv.config({ path: path.join(__dirname, '../../backend/.env') });

async function createDatabase() {
  // Connect to PostgreSQL (default 'postgres' database to create new database)
  const adminUrl = process.env.DATABASE_URL?.replace(/\/rolley/, '/postgres') || 
    'postgresql://postgres:PHYSICS1234@localhost:5432/postgres?schema=public';
  
  const adminPrisma = new PrismaClient({
    datasources: {
      db: {
        url: adminUrl
      }
    }
  });

  try {
    // Create database if not exists
    await adminPrisma.$executeRawUnsafe(
      `CREATE DATABASE IF NOT EXISTS football_ai;`
    );
    console.log('✅ Database "football_ai" created (or already exists)');
    
    // Close admin connection
    await adminPrisma.$disconnect();
    
    // Test connection to new database
    const footballDbUrl = process.env.DATABASE_URL?.replace(/\/rolley/, '/football_ai') ||
      'postgresql://postgres:PHYSICS1234@localhost:5432/football_ai?schema=public';
    
    const testPrisma = new PrismaClient({
      datasources: {
        db: {
          url: footballDbUrl
        }
      }
    });
    
    await testPrisma.$queryRaw`SELECT 1`;
    await testPrisma.$disconnect();
    
    console.log('✅ Successfully connected to football_ai database');
    console.log('\n📝 Use this connection string in football-safe-ai/.env:');
    console.log(`FOOTBALL_AI_DATABASE_URL=${footballDbUrl}`);
    
  } catch (error: any) {
    console.error('❌ Error:', error.message);
    console.log('\nAlternative: Use the same database as Rolley:');
    console.log('FOOTBALL_AI_DATABASE_URL=postgresql://postgres:PHYSICS1234@localhost:5432/rolley?schema=public');
  }
}

createDatabase();


