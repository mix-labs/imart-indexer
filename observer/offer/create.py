from typing import List, Tuple
from model.coin_type_info import CoinTypeInfo
from model.token_id import TokenId, TokenDataId
from observer.observer import Observer
from model.offer.create_offer_event import CreateOfferEvent, CreateOfferEventData
from model.state import State
from model.event import Event
from common.db import prisma_client
from prisma import enums
from datetime import datetime
from prisma.fields import Base64
from common.util import new_uuid_hex_bytes


class CreateOfferEventObserver(Observer[CreateOfferEvent]):

    async def process_all(self, state: State, events: List[Event[CreateOfferEvent]]) -> State:
        return await super().process_all(state, events)

    async def process(self, state: State, event: Event[CreateOfferEvent]) -> Tuple[State, bool]:
        new_state = state
        seqno = int(event.sequence_number)
        data = CreateOfferEventData(**event.data)
        token_data_id = TokenDataId(**TokenId(**data.token_id).token_data_id)
        coin_type_info = CoinTypeInfo(**data.coin_type_info)

        token = await prisma_client.aptostoken.find_first(where={
            'name': token_data_id.name,
            'creator': token_data_id.creator,
            'collection': token_data_id.collection,
        })
        if token == None:
            raise Exception(
                f'[Create offer]: Token({token_data_id}) not found, but created offer event({data}) was existed')

        async with prisma_client.tx(timeout=60000) as transaction:
            # convert microseconds to milliseconds
            openedAt = datetime.fromtimestamp(
                float(data.timestamp) / 1000000
            )
            endedAt = datetime.fromtimestamp(
                float(data.expiration_time) / 1000000
            )
            id = Base64.encode(new_uuid_hex_bytes())
            result = await transaction.aptosoffer.create(
                data={
                    'id': id,
                    'collectionId': token.collectionId,
                    'tokenId': token.id,
                    'price': float(data.coin_amount_per_token),
                    'quantity': int(data.token_amount),
                    'currency': coin_type_info.currency(),
                    'offerer': data.coin_owner,
                    'openedAt': openedAt,
                    'endedAt': endedAt,
                    'status':  enums.OfferStatus.CREATED
                }
            )
            if result == None or result.status != enums.OfferStatus.CREATED:
                raise Exception(
                    f'[Create Offer]: Failed to create new offer({data}) for the token({token})')

            updated_offset = await transaction.eventoffset.update(
                where={'id': 0},
                data={
                    "create_offer_excuted_offset": seqno
                }
            )
            if updated_offset == None:
                raise Exception(f'[Create Offer]: Failed to update offset')

            new_state.new_offset.create_offer_excuted_offset = updated_offset.create_offer_excuted_offset
            return new_state, True
