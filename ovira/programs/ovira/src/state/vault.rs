use anchor_lang::prelude::*;

use crate::constant::VAULT_CONFIG_SEED;

#[account]
pub struct VaultConfig {
    pub admin: Pubkey,
    pub token_mint: Pubkey,   
    pub performance_fee: u16,      
    pub management_fee: u16,   
    pub bump: [u8; 1],     
}

impl VaultConfig{
    pub fn auth_seeds<'a>(&'a self) -> [&'a [u8]; 3] {
        [
            VAULT_CONFIG_SEED,
            self.token_mint.as_ref(),
            self.bump.as_ref(),
        ]
    }
}

pub const VAULT_CONFIG_SIZE: usize = 8 + 32 + 32 + 2 + 2 + 1;

#[account]
pub struct Vault {
    pub total_shares: u64,
    pub toltal_assets: u64,    
    pub unallocated_amount: u64,
    pub pools: Vec<Pool>, 
}

pub const VAULT_SIZE: usize =
    8 +
    8 +
    8 +
    8 +
    4 + 15 * 150;

#[derive(AnchorSerialize, AnchorDeserialize, Clone)]
pub struct Pool {
    pub id: String,
    pub allocation_percentage: u8,
    pub amount: u64,
}
