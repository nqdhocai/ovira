use anchor_lang::prelude::*;
use anchor_spl::{associated_token::AssociatedToken, token::{Mint, Token, TokenAccount}};

use crate::{constant::{USER_POSITION_SEED, VAULT_CONFIG_SEED, VAULT_SEED}, transfer_token_with_signer, UserPosition, Vault, VaultConfig, USER_POSITION_SIZE};

#[derive(Accounts)]
pub struct WithDraw<'info> { 
    #[account(mut)]
    pub signer: Signer<'info>,

    #[account(
        init_if_needed,
        payer = signer,
        space = USER_POSITION_SIZE,
        seeds = [
            USER_POSITION_SEED,
            token_mint.key().as_ref(),
            signer.key().as_ref(),
        ],
        bump,
    )]
    pub user_position: Box<Account<'info, UserPosition>>,

    #[account(
        mut, 
        seeds = [
            VAULT_SEED,
            token_mint.key().as_ref()
        ],
        bump,
    )]
    pub vault: Box<Account<'info, Vault>>,

    #[account(
        mut, 
        seeds = [
            VAULT_CONFIG_SEED,
            token_mint.key().as_ref()
        ], 
        bump,
    )]
    pub vault_config: Box<Account<'info, VaultConfig>>,

    #[account(
        mut,
        associated_token::mint = token_mint,
        associated_token::authority = vault_config,
    )]
    pub vault_token_account: Box<Account<'info, TokenAccount>>,

    #[account(
        mut, 
        associated_token::mint = token_mint,
        associated_token::authority = signer,
    )]
    pub user_token_account: Box<Account<'info, TokenAccount>>,

    pub token_mint: Box<Account<'info, Mint>>,

    pub associated_token_program: Program<'info, AssociatedToken>,

    pub token_program: Program<'info, Token>,

    pub system_program: Program<'info, System>,

    pub rent: Sysvar<'info, Rent>,
}

impl<'info> WithDraw<'info> {
    pub fn process(&mut self, amount: u64) -> Result<()> {
        transfer_token_with_signer(
            self.vault_token_account.to_account_info(), 
            self.vault_config.to_account_info(), 
            self.user_token_account.to_account_info(), 
            &[&self.vault_config.auth_seeds()],
            &self.token_program, 
            amount,
        )?;
        
        Ok(())
    }
}