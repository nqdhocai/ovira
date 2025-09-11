use anchor_lang::prelude::*;

#[account]
pub struct UserPosition {
    pub share: u64,
    pub amount: u64,
}

pub const USER_POSITION_SIZE: usize = 8 + 8 + 8;