use anchor_lang::prelude::*;

declare_id!("J5gfukL3DuPouDpLC9raJvPF36SxQ8LQirMh2SrVusgr");

mod constant;
mod error;
mod util;
pub use util::*;

pub mod instructions;
pub use instructions::*;

pub mod state;
pub use state::*;

pub mod pool;
pub use pool::*;



#[program]
pub mod ovira {
    use super::*;

    pub fn initialize(
        ctx: Context<Initialize>,
        performance_fee: u16,
        management_fee: u16,
        pools: Vec<String>,
    ) -> Result<()> {
        ctx.accounts.process(performance_fee, management_fee, &ctx.bumps, pools)
    }

    pub fn deposit(
        ctx: Context<Deposit>,
        amount: u64
    ) -> Result<()> {
        ctx.accounts.process(amount)
    }

    pub fn withdraw(
        ctx: Context<WithDraw>,
        amount: u64
    ) -> Result<()> {
        ctx.accounts.process(amount)
    }
}
