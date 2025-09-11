use anchor_lang::prelude::*;
use anchor_spl::{
    associated_token::AssociatedToken,
    token::{Mint, Token, TokenAccount}
};

use crate::{
    constant::{VAULT_CONFIG_SEED, VAULT_SEED},
    state::{Vault, VaultConfig, VAULT_CONFIG_SIZE, VAULT_SIZE}, Pool,
};

#[derive(Accounts)]
pub struct Initialize<'info> {
    #[account(mut)]
    pub admin: Signer<'info>,

    #[account(
        init,
        payer = admin,
        space = VAULT_CONFIG_SIZE,
        seeds = [
            VAULT_CONFIG_SEED,
            token_mint.key().as_ref(),
        ],
        bump,
    )]
    pub vault_config: Box<Account<'info, VaultConfig>>,

    #[account(
        init,
        payer = admin,
        space = VAULT_SIZE,
        seeds = [
            VAULT_SEED,
            token_mint.key().as_ref(),
        ],
        bump,
    )]
    pub vault: Box<Account<'info, Vault>>,

    #[account(
        associated_token::mint = token_mint,
        associated_token::authority = vault_config,
    )]
    pub vault_token_account: Box<Account<'info, TokenAccount>>,

    pub token_mint: Box<Account<'info, Mint>>,

    pub associated_token_program: Program<'info, AssociatedToken>,
    pub token_program: Program<'info, Token>,
    pub system_program: Program<'info, System>,
    pub rent: Sysvar<'info, Rent>,
}

impl<'info> Initialize<'info> {
    pub fn process(
        &mut self,
        performance_fee: u16,
        management_fee: u16,
        bumps: &InitializeBumps,
        pools: Vec<String>,
    ) -> Result<()> {
        self.vault_config.set_inner(VaultConfig {
            admin: self.admin.key(),
            token_mint: self.token_mint.key(),
            performance_fee,
            management_fee,
            bump: [bumps.vault_config],
        });

        let pool_list: Vec<Pool> = pools
            .into_iter()
            .map( |id| Pool {
                id: id,
                allocation_percentage: 0,
                amount: 0,
            })
            .collect();

        self.vault.set_inner(Vault {
            total_shares: 0,
            toltal_assets: 0,
            unallocated_amount: 0,
            pools: pool_list,
        });

        Ok(())
    }
}
