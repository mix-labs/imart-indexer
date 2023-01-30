from typing import List, Tuple
from observer.observer import Observer
from model.curation.offer_create_event import OfferCreateEvent, OfferCreateEventData
from model.state import State
from model.event import Event
from model.token_id import TokenDataId, TokenId
from common.db import prisma_client
from prisma import enums
from datetime import datetime
from common.util import new_uuid
from config import config


class OfferCreateEventObserver(Observer[OfferCreateEvent]):

    async def process_all(self, state: State, events: List[Event[OfferCreateEvent]]) -> State:
        return await super().process_all(state, events)

    async def process(self, state: State, event: Event[OfferCreateEvent]) -> Tuple[State, bool]:
        new_state = state
        seqno = event.sequence_number
        data = OfferCreateEventData(**event.data)
        index = int(data.id)
        gallery_index = int(data.gallery_id)
        token_id = TokenId(**data.token_id)
        token_data_id = TokenDataId(**token_id.token_data_id)
        updated_at = datetime.fromtimestamp(int(data.offer_start_at))
        offer_start_at = datetime.fromtimestamp(int(data.offer_start_at))
        offer_expired_at = datetime.fromtimestamp(int(data.offer_expired_at))
        exhibit_duration = int(data.exhibit_duration)
        commission_feerate = 10**8 * \
            int(data.commission_feerate_numerator) // \
            int(data.commission_feerate_denominator)

        root = config.curation.address()

        async with prisma_client.tx(timeout=60000) as transaction:
            result = await transaction.curationoffer.upsert(
                where={
                    'index_root': {
                        'index': index,
                        'root': root
                    }
                },
                data={
                    'create': {
                        'id': new_uuid(),
                        'index': index,
                        'root': root,
                        'galleryIndex': gallery_index,
                        'collection': token_data_id.collection,
                        'tokenName': token_data_id.name,
                        'tokenCreator': token_data_id.creator,
                        'propertyVersion': 0,
                        'source': data.source,
                        'destination': data.destination,
                        'price': data.price,
                        'commissionFeeRate': str(commission_feerate),
                        'offerStartAt': offer_start_at,
                        'offerExpiredAt': offer_expired_at,
                        'exhibitDuration': exhibit_duration,
                        'status': enums.CurationOfferStatus.pending,
                        'updatedAt': updated_at,
                        'url': data.url,
                        'detail': data.detail
                    },
                    'update': {
                        'galleryIndex': gallery_index,
                        'collection': token_data_id.collection,
                        'tokenName': token_data_id.name,
                        'tokenCreator': token_data_id.creator,
                        'propertyVersion': 0,
                        'source': data.source,
                        'destination': data.destination,
                        'price': data.price,
                        'commissionFeeRate': str(commission_feerate),
                        'offerStartAt': offer_start_at,
                        'offerExpiredAt': offer_expired_at,
                        'exhibitDuration': exhibit_duration,
                        'status': enums.CurationOfferStatus.pending,
                        'updatedAt': updated_at,
                        'url': data.url,
                        'detail': data.detail
                    }
                }
            )
            if result == None or result.status != enums.CurationOfferStatus.pending:
                raise Exception(
                    f'[Curator send offer]: Failed to create curation offer({data})')

            updated_offset = await transaction.eventoffset.update(
                where={'id': 0},
                data={
                    "curation_offer_create_excuted_offset": int(seqno)
                }
            )
            if updated_offset == None:
                raise Exception(
                    f'[Curator send Offer]: Failed to update offset')

            await transaction.notification.upsert(
                where={
                    'receiver_type_timestamp': {
                        'receiver': data.destination,
                        'type': enums.NotificationType.CurationOfferReceivedFromInviter,
                        'timestamp': offer_start_at
                    }
                },
                data={
                    'create': {
                        'id': new_uuid(),
                        'receiver': data.destination,
                        'title': "You have received an offer",
                        'content': "From Mixverse",
                        'image': "",
                        'type': enums.NotificationType.CurationOfferReceivedFromInviter,
                        'unread': True,
                        'timestamp': offer_start_at,
                        'detail': f'{{"index": {gallery_index}, "root": {root}}}'
                    },
                    'update': {
                        'receiver': data.destination,
                        'title': "You have received an offer",
                        'content': "From Mixverse",
                        'image': "",
                        'type': enums.NotificationType.CurationOfferReceivedFromInviter,
                        'unread': True,
                        'timestamp': offer_start_at,
                        'detail': f'{{"index": {gallery_index}, "root": {root}}}'
                    }
                }
            )
            new_state.new_offset.curation_offer_create_excuted_offset = updated_offset.curation_offer_create_excuted_offset
            return new_state, True
